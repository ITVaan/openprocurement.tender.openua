from openprocurement.api.validation import validate_data, validate_json_data, OPERATIONS
from openprocurement.api.utils import apply_data_patch, error_handler, get_now, raise_operation_error
from openprocurement.tender.core.utils import calculate_business_date


def validate_patch_tender_ua_data(request):
    data = validate_json_data(request)
    # TODO try to use original code openprocurement.tender.core.validation.validate_patch_tender_data
    if request.context.status == 'draft':
        default_status = type(request.tender).fields['status'].default
        if data and data.get('status') != default_status:
            raise_operation_error(request, 'Can\'t update tender in current (draft) status')
        request.validated['data'] = {'status': default_status}
        request.context.status = default_status
        return
    if data:
        if 'items' in data:
            items = request.context.items
            cpv_group_lists = [i.classification.id[:3] for i in items]
            for item in data['items']:
                if 'classification' in item and 'id' in item['classification']:
                    cpv_group_lists.append(item['classification']['id'][:3])
            if len(set(cpv_group_lists)) != 1:
                request.errors.add('body', 'item', 'Can\'t change classification')
                request.errors.status = 403
                raise error_handler(request.errors)
        if 'enquiryPeriod' in data:
            if apply_data_patch(request.context.enquiryPeriod.serialize(), data['enquiryPeriod']):
                request.errors.add('body', 'item', 'Can\'t change enquiryPeriod')
                request.errors.status = 403
                raise error_handler(request.errors)

    return validate_data(request, type(request.tender), True, data)


# bids
def validate_update_bid_to_draft(request):
    bid_status_to = request.validated['data'].get("status", request.context.status)
    if request.context.status != 'draft' and bid_status_to == 'draft':
        request.errors.add('body', 'bid', 'Can\'t update bid to ({}) status'.format(bid_status_to))
        request.errors.status = 403
        raise error_handler(request.errors)


def validate_update_bid_to_active_status(request):
    bid_status_to = request.validated['data'].get("status", request.context.status)
    if bid_status_to != request.context.status and bid_status_to != 'active':
        request.errors.add('body', 'bid', 'Can\'t update bid to ({}) status'.format(bid_status_to))
        request.errors.status = 403
        raise error_handler(request.errors)


def validate_add_complaint_not_in_allowed_tender_status(request):
    tender = request.context
    if tender.status not in ['active.enquiries', 'active.tendering']:
        raise_operation_error(request, 'Can\'t add complaint in current ({}) tender status'.format(tender.status))


def validate_update_complaint_not_in_allowed_tender_status(request):
    tender = request.validated['tender']
    if tender.status not in ['active.enquiries', 'active.tendering', 'active.auction', 'active.qualification',
                             'active.awarded']:
        raise_operation_error(request, 'Can\'t update complaint in current ({}) tender status'.format(tender.status))


def validate_update_complaint_not_in_allowed_status(request):
    if request.context.status not in ['draft', 'claim', 'answered', 'pending']:
        raise_operation_error(request, 'Can\'t update complaint in current ({}) status'.format(request.context.status))


# complaint
def validate_submit_claim_time(request):
    tender = request.context
    claim_submit_time = request.content_configurator.tender_claim_submit_time
    if get_now() > calculate_business_date(tender.tenderPeriod.endDate, -claim_submit_time, tender):
        raise_operation_error(request,
                              'Can submit claim not later than {0.days} days before tenderPeriod end'.format(
                                  claim_submit_time))


# complaint document
def validate_complaint_document_operation_not_in_allowed_status(request):
    if request.validated['tender_status'] not in ['active.enquiries', 'active.tendering', 'active.auction',
                                                  'active.qualification', 'active.awarded']:
        raise_operation_error(request,
                              'Can\'t {} document in current ({}) tender status'.format(OPERATIONS.get(request.method),
                                                                                        request.validated[
                                                                                            'tender_status']))


def validate_role_and_status_for_add_complaint_document(request):
    roles = request.content_configurator.allowed_statuses_for_complaint_operations_for_roles
    if request.context.status not in roles.get(request.authenticated_role, []):
        raise_operation_error(request,
                              'Can\'t add document in current ({}) complaint status'.format(request.context.status))


# auction
def validate_auction_info_view(request):
    if request.validated['tender_status'] != 'active.auction':
        raise_operation_error(request, 'Can\'t get auction info in current ({}) tender status'.format(
            request.validated['tender_status']))


# award
def validate_create_award_not_in_allowed_period(request):
    tender = request.validated['tender']
    if tender.status != 'active.qualification':
        raise_operation_error(request, 'Can\'t create award in current ({}) tender status'.format(tender.status))


def validate_create_award_only_for_active_lot(request):
    tender = request.validated['tender']
    award = request.validated['award']
    if any([i.status != 'active' for i in tender.lots if i.id == award.lotID]):
        raise_operation_error(request, 'Can create award only in active lot status')


def validate_cancel_award_of_merged_contracts(request):
    tender = request.validated['tender']
    award = request.validated['award']
    if request.validated['data'].get('status') == 'cancelled' and [
        i for i in tender.contracts if i.awardID == award.id and i.status == 'merged'
    ]:
        raise_operation_error(request, 'Can\'t cancel award while it is a part of merged contracts.')


# award complaint
def validate_award_complaint_update_not_in_allowed_status(request):
    if request.context.status not in ['draft', 'claim', 'answered']:
        raise_operation_error(request, 'Can\'t update complaint in current ({}) status'.format(request.context.status))


# contract document
def validate_cancellation_document_operation_not_in_allowed_status(request):
    if request.validated['tender_status'] in ['complete', 'cancelled', 'unsuccessful']:
        raise_operation_error(request,
                              'Can\'t {} document in current ({}) tender status'.format(OPERATIONS.get(request.method),
                                                                                        request.validated[
                                                                                            'tender_status']))


# contract
def validate_contract_update_with_accepted_complaint(request):
    tender = request.validated['tender']
    if any([any([c.status == 'accepted' for c in i.complaints]) for i in tender.awards if
            i.lotID in [a.lotID for a in tender.awards if a.id == request.context.awardID]]):
        raise_operation_error(request, 'Can\'t update contract with accepted complaint')
