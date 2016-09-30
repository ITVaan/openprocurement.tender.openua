# -*- coding: utf-8 -*-
from openprocurement.api.models import get_now
from openprocurement.api.views.contract import TenderAwardContractResource
from openprocurement.api.utils import (
    apply_patch,
    check_tender_status,
    context_unpack,
    json_view,
    opresource,
    save_tender,
)
from openprocurement.api.validation import validate_patch_contract_data


@opresource(name='Tender UA Contracts',
            collection_path='/tenders/{tender_id}/contracts',
            path='/tenders/{tender_id}/contracts/{contract_id}',
            procurementMethodType='aboveThresholdUA',
            description="Tender contracts")
class TenderUaAwardContractResource(TenderAwardContractResource):

    def check_merged_contracts(self):
        """ Set status pending and delete mergeInto for all previous merged contracts before
            Set status merged and set mergeInto for all new contracts which awardID come in additionalAwardIDs """

        contract = self.request.validated['contract']
        data = self.request.validated['data']
        tender = self.request.validated['tender']
        if 'additionalAwardIDs' in contract:  # Get ids for all previos merged contracts
            old_additional_award_ids = [additional_award_id['id'] for additional_award_id in contract.get('additionalAwardIDs', [])]
            new_additional_award_ids = [additional_award_id['id'] for additional_award_id in data['additionalAwardIDs']]
            prev_contracts = [prev_contract for prev_contract in tender['contracts'] if
                              prev_contract['awardID'] in old_additional_award_ids]

            new_contracts = [new_contract for new_contract in tender['contracts'] if
                             new_contract['awardID'] in new_additional_award_ids]
            for new_contract in new_contracts:
                # all new contracts must have status pending
                if new_contract['status'] != 'pending' and new_contract not in prev_contracts:
                    self.request.errors.add('body', 'data', 'All additional must have status pending')
                    self.request.errors.status = 403
                    return
                # Check if it exists and length > 0
                if 'additionalAwardIDs' in new_contract and new_contract['additionalAwardIDs']:
                    self.request.errors.add('body', 'data', "Can't merge contracts for contract which merge another id={}".format(new_contract['id']))
                    self.request.errors.status = 403
                    return

            for prev_contract in prev_contracts:
                prev_contract['status'] = 'pending'
                del prev_contract['mergedInto']

            for new_contract in new_contracts:
                new_contract['status'] = 'merged'
                new_contract['mergedInto'] = contract['id']

    @json_view(content_type="application/json", permission='edit_tender', validators=(validate_patch_contract_data,))
    def patch(self):
        """Update of contract
        """
        if self.request.validated['contract']['status'] == 'merged':
            self.request.errors.add('body', 'data', 'Can\'t update contract in current ({}) status'.format(self.request.validated['contract']['status']))
            self.request.errors.status = 403
            return
        if self.request.validated['tender_status'] not in ['active.qualification', 'active.awarded']:
            self.request.errors.add('body', 'data', 'Can\'t update contract in current ({}) tender status'.format(self.request.validated['tender_status']))
            self.request.errors.status = 403
            return
        tender = self.request.validated['tender']
        if any([i.status != 'active' for i in tender.lots if i.id in [a.lotID for a in tender.awards if a.id == self.request.context.awardID]]):
            self.request.errors.add('body', 'data', 'Can update contract only in active lot status')
            self.request.errors.status = 403
            return
        if any([any([c.status == 'accepted' for c in i.complaints]) for i in tender.awards if i.lotID in [a.lotID for a in tender.awards if a.id == self.request.context.awardID]]):
            self.request.errors.add('body', 'data', 'Can\'t update contract with accepted complaint')
            self.request.errors.status = 403
            return
        data = self.request.validated['data']

        if data['value']:
            for ro_attr in ('valueAddedTaxIncluded', 'currency'):
                if data['value'][ro_attr] != getattr(self.context.value, ro_attr):
                    self.request.errors.add('body', 'data', 'Can\'t update {} for contract value'.format(ro_attr))
                    self.request.errors.status = 403
                    return

            award = [a for a in tender.awards if a.id == self.request.context.awardID][0]
            if data['value']['amount'] > award.value.amount:
                self.request.errors.add('body', 'data', 'Value amount should be less or equal to awarded amount ({})'.format(award.value.amount))
                self.request.errors.status = 403
                return

        if self.request.context.status != 'active' and 'status' in data and data['status'] == 'active':
            award = [a for a in tender.awards if a.id == self.request.context.awardID][0]
            stand_still_end = award.complaintPeriod.endDate
            if stand_still_end > get_now():
                self.request.errors.add('body', 'data', 'Can\'t sign contract before stand-still period end ({})'.format(stand_still_end.isoformat()))
                self.request.errors.status = 403
                return
            pending_complaints = [
                i
                for i in tender.complaints
                if i.status in tender.block_complaint_status and i.relatedLot in [None, award.lotID]
            ]
            pending_awards_complaints = [
                i
                for a in tender.awards
                for i in a.complaints
                if i.status in tender.block_complaint_status and a.lotID == award.lotID
            ]
            if pending_complaints or pending_awards_complaints:
                self.request.errors.add('body', 'data', 'Can\'t sign contract before reviewing all complaints')
                self.request.errors.status = 403
                return
        contract_status = self.request.context.status
        apply_patch(self.request, save=False, src=self.request.context.serialize())
        if contract_status != self.request.context.status and (contract_status != 'pending' or self.request.context.status != 'active'):
            self.request.errors.add('body', 'data', 'Can\'t update contract status')
            self.request.errors.status = 403
            return
        if self.request.context.status == 'active' and not self.request.context.dateSigned:
            self.request.context.dateSigned = get_now()
        check_tender_status(self.request)
        if save_tender(self.request):
            self.LOGGER.info('Updated tender contract {}'.format(self.request.context.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_contract_patch'}))
            return {'data': self.request.context.serialize()}
