# -*- coding: utf-8 -*-
from datetime import timedelta
from logging import getLogger

from barbecue import chef
from openprocurement.api.constants import TZ, SANDBOX_MODE
from openprocurement.api.utils import get_now
from openprocurement.tender.belowthreshold.utils import (
    check_tender_status,
    context_unpack,
)
from openprocurement.tender.core.constants import COMPLAINT_STAND_STILL_TIME
from openprocurement.tender.core.utils import (
    calculate_business_date, cleanup_bids_for_cancelled_lots,
    remove_draft_bids
)
from openprocurement.tender.openua.constants import (
    NORMALIZED_COMPLAINT_PERIOD_FROM
)
from pkg_resources import get_distribution

PKG = get_distribution(__package__)
LOGGER = getLogger(PKG.project_name)


def calculate_normalized_date(dt, tender, ceil=False):
    if (tender.revisions[0].date if tender.revisions else get_now()) > NORMALIZED_COMPLAINT_PERIOD_FROM and \
            not (SANDBOX_MODE and tender.procurementMethodDetails):
        if ceil:
            return dt.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return dt.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return dt


def check_bids(request):
    tender = request.validated['tender']
    if tender.lots:
        [setattr(i.auctionPeriod, 'startDate', None) for i in tender.lots if
         i.numberOfBids < 2 and i.auctionPeriod and i.auctionPeriod.startDate]
        [setattr(i, 'status', 'unsuccessful') for i in tender.lots if i.numberOfBids == 0 and i.status == 'active']
        cleanup_bids_for_cancelled_lots(tender)
        if not set([i.status for i in tender.lots]).difference(set(['unsuccessful', 'cancelled'])):
            tender.status = 'unsuccessful'
        elif max([i.numberOfBids for i in tender.lots if i.status == 'active']) < 2:
            add_next_award(request)
    else:
        if tender.numberOfBids < 2 and tender.auctionPeriod and tender.auctionPeriod.startDate:
            tender.auctionPeriod.startDate = None
        if tender.numberOfBids == 0:
            tender.status = 'unsuccessful'
        if tender.numberOfBids == 1:
            # tender.status = 'active.qualification'
            add_next_award(request)
    check_ignored_claim(tender)


def check_complaint_status(request, complaint, now=None):
    if not now:
        now = get_now()
    if complaint.status == 'answered' and calculate_business_date(complaint.dateAnswered, COMPLAINT_STAND_STILL_TIME,
                                                                  request.tender) < now:
        complaint.status = complaint.resolutionType
    elif complaint.status == 'pending' and complaint.resolutionType and complaint.dateEscalated:
        complaint.status = complaint.resolutionType
    elif complaint.status == 'pending':
        complaint.status = 'ignored'


def check_ignored_claim(tender):
    complete_lot_ids = [None] if tender.status in ['complete', 'cancelled', 'unsuccessful'] else []
    complete_lot_ids.extend([i.id for i in tender.lots if i.status in ['complete', 'cancelled', 'unsuccessful']])
    for complaint in tender.complaints:
        if complaint.status == 'claim' and complaint.relatedLot in complete_lot_ids:
            complaint.status = 'ignored'
    for award in tender.awards:
        for complaint in award.complaints:
            if complaint.status == 'claim' and complaint.relatedLot in complete_lot_ids:
                complaint.status = 'ignored'


def check_status(request):
    tender = request.validated['tender']
    now = get_now()
    for complaint in tender.complaints:
        check_complaint_status(request, complaint, now)
    for award in tender.awards:
        if award.status == 'active' and not any([i.awardID == award.id for i in tender.contracts]):
            tender.contracts.append(type(tender).contracts.model_class({
                'awardID': award.id,
                'suppliers': award.suppliers,
                'value': award.value,
                'date': now,
                'items': [i for i in tender.items if i.relatedLot == award.lotID],
                'contractID': '{}-{}{}'.format(tender.tenderID, request.registry.server_id,
                                               len(tender.contracts) + 1)}))
            add_next_award(request)
        for complaint in award.complaints:
            check_complaint_status(request, complaint, now)
    if tender.status == 'active.enquiries' and not tender.tenderPeriod.startDate and tender.enquiryPeriod.endDate.astimezone(
            TZ) <= now:
        LOGGER.info('Switched tender {} to {}'.format(tender.id, 'active.tendering'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_active.tendering'}))
        tender.status = 'active.tendering'
        return
    elif tender.status == 'active.enquiries' and tender.tenderPeriod.startDate and tender.tenderPeriod.startDate.astimezone(
            TZ) <= now:
        LOGGER.info('Switched tender {} to {}'.format(tender.id, 'active.tendering'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_active.tendering'}))
        tender.status = 'active.tendering'
        return
    elif not tender.lots and tender.status == 'active.tendering' and tender.tenderPeriod.endDate <= now:
        LOGGER.info('Switched tender {} to {}'.format(tender['id'], 'active.auction'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_active.auction'}))
        tender.status = 'active.auction'
        remove_draft_bids(request)
        check_bids(request)
        if tender.numberOfBids < 2 and tender.auctionPeriod:
            tender.auctionPeriod.startDate = None
        return
    elif tender.lots and tender.status == 'active.tendering' and tender.tenderPeriod.endDate <= now:
        LOGGER.info('Switched tender {} to {}'.format(tender['id'], 'active.auction'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_active.auction'}))
        tender.status = 'active.auction'
        remove_draft_bids(request)
        check_bids(request)
        [setattr(i.auctionPeriod, 'startDate', None) for i in tender.lots if i.numberOfBids < 2 and i.auctionPeriod]
        return
    elif not tender.lots and tender.status == 'active.awarded':
        standStillEnds = [
            a.complaintPeriod.endDate.astimezone(TZ)
            for a in tender.awards
            if a.complaintPeriod.endDate
        ]
        if not standStillEnds:
            return
        standStillEnd = max(standStillEnds)
        if standStillEnd <= now:
            check_tender_status(request)
    elif tender.lots and tender.status in ['active.qualification', 'active.awarded']:
        if any([i['status'] in tender.block_complaint_status and i.relatedLot is None for i in tender.complaints]):
            return
        for lot in tender.lots:
            if lot['status'] != 'active':
                continue
            lot_awards = [i for i in tender.awards if i.lotID == lot.id]
            standStillEnds = [
                a.complaintPeriod.endDate.astimezone(TZ)
                for a in lot_awards
                if a.complaintPeriod.endDate
            ]
            if not standStillEnds:
                continue
            standStillEnd = max(standStillEnds)
            if standStillEnd <= now:
                check_tender_status(request)
                return


def get_contract_by_id(contract_id, tender):
    for contract in tender.contracts:
        if contract_id == contract['id']:
            return contract


def add_next_award(request, reverse=False, awarding_criteria_key='amount'):
    """Adding next award.
    :param request:
        The pyramid request object.
    :param reverse:
        Is used for sorting bids to generate award.
        By default (reverse = False) awards are generated from lower to higher by value.amount
        When reverse is set to True awards are generated from higher to lower by value.amount
    """
    tender = request.validated['tender']
    now = get_now()
    if not tender.awardPeriod:
        tender.awardPeriod = type(tender).awardPeriod({})
    if not tender.awardPeriod.startDate:
        tender.awardPeriod.startDate = now
    if tender.lots:
        statuses = set()
        for lot in tender.lots:
            if lot.status != 'active':
                continue
            lot_awards = [i for i in tender.awards if i.lotID == lot.id]
            if lot_awards and lot_awards[-1].status in ['pending', 'active']:
                statuses.add(lot_awards[-1].status if lot_awards else 'unsuccessful')
                continue
            lot_items = [i.id for i in tender.items if i.relatedLot == lot.id]
            features = [
                i
                for i in (tender.features or [])
                if
                i.featureOf == 'tenderer' or i.featureOf == 'lot' and i.relatedItem == lot.id or i.featureOf == 'item' and i.relatedItem in lot_items
            ]
            codes = [i.code for i in features]
            bids = [
                {
                    'id': bid.id,
                    'value': [i for i in bid.lotValues if lot.id == i.relatedLot][0].value.serialize(),
                    'tenderers': bid.tenderers,
                    'parameters': [i for i in bid.parameters if i.code in codes],
                    'date': [i for i in bid.lotValues if lot.id == i.relatedLot][0].date
                }
                for bid in tender.bids
                if bid.status == "active" and lot.id in [i.relatedLot for i in bid.lotValues if
                                                         getattr(i, 'status', "active") == "active"]
            ]
            if not bids:
                lot.status = 'unsuccessful'
                statuses.add('unsuccessful')
                continue
            unsuccessful_awards = [i.bid_id for i in lot_awards if i.status == 'unsuccessful']
            bids = chef(bids, features, unsuccessful_awards, reverse)
            if bids:
                bid = bids[0]
                award = tender.__class__.awards.model_class({
                    'bid_id': bid['id'],
                    'lotID': lot.id,
                    'status': 'pending',
                    'date': get_now(),
                    'value': bid['value'],
                    'suppliers': bid['tenderers'],
                    'complaintPeriod': {
                        'startDate': now.isoformat()
                    }
                })
                award.__parent__ = tender
                tender.awards.append(award)
                request.response.headers['Location'] = request.route_url(
                    '{}:Tender Awards'.format(tender.procurementMethodType), tender_id=tender.id, award_id=award['id'])
                statuses.add('pending')
            else:
                statuses.add('unsuccessful')
        if statuses.difference(set(['unsuccessful', 'active'])):
            tender.awardPeriod.endDate = None
            tender.status = 'active.qualification'
        else:
            tender.awardPeriod.endDate = now
            tender.status = 'active.awarded'
    else:
        if not tender.awards or tender.awards[-1].status not in ['pending', 'active']:
            unsuccessful_awards = [i.bid_id for i in tender.awards if i.status == 'unsuccessful']
            codes = [i.code for i in tender.features or []]
            active_bids = [
                {
                    'id': bid.id,
                    'value': bid.value.serialize(),
                    'tenderers': bid.tenderers,
                    'parameters': [i for i in bid.parameters if i.code in codes],
                    'date': bid.date
                }
                for bid in tender.bids
                if bid.status == "active"
            ]
            bids = chef(active_bids, tender.features or [], unsuccessful_awards, reverse)
            if bids:
                bid = bids[0]
                award = tender.__class__.awards.model_class({
                    'bid_id': bid['id'],
                    'status': 'pending',
                    'date': get_now(),
                    'value': bid['value'],
                    'suppliers': bid['tenderers'],
                    'complaintPeriod': {
                        'startDate': get_now().isoformat()
                    }
                })
                award.__parent__ = tender
                tender.awards.append(award)
                request.response.headers['Location'] = request.route_url(
                    '{}:Tender Awards'.format(tender.procurementMethodType), tender_id=tender.id, award_id=award['id'])
        if tender.awards[-1].status == 'pending':
            tender.awardPeriod.endDate = None
            tender.status = 'active.qualification'
        else:
            tender.awardPeriod.endDate = now
            tender.status = 'active.awarded'
