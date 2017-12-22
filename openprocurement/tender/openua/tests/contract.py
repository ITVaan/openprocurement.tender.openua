# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy

from openprocurement.api.tests.base import snitch
from openprocurement.tender.belowthreshold.tests.base import test_organization, test_lots
from openprocurement.tender.openua.tests.base import (
    test_bids, BaseTenderUAContentWebTest
)
from openprocurement.tender.openua.tests.contract_blanks import (
    # TenderContractResourceTest
    create_tender_contract_invalid,
    create_tender_contract,
    patch_tender_contract_datesigned,
    patch_tender_contract,
    get_tender_contract,
    get_tender_contracts,
    # TenderContractDocumentResourceTest
    not_found,
    create_tender_contract_document,
    put_tender_contract_document,
    patch_tender_contract_document,
    # TenderMergedContracts2LotsResourceTest
    not_found_contract_for_award_2,
    try_merge_not_real_award_2,
    try_merge_itself_2,
    merge_two_contracts_2,
    standstill_period_2,
    additional_awards_dateSigned_2,
    activate_contract_with_complaint_2,
    cancel_award_2,
    cancel_main_award_2,
    merge_two_contracts_with_different_suppliers_id_2,
    merge_two_contracts_with_different_suppliers_scheme_2,
    set_big_value_2,
    # TenderMergedContracts3LotsResourceTest
    merge_three_contracts_3,
    standstill_period_3,
    activate_contract_with_complaint_3,
    cancel_award_3,
    cancel_main_award_3,
    try_merge_pending_award_3,
    additional_awards_dateSigned_3,
    # TenderMergedContracts4LotsResourceTest
    merge_four_contracts_4,
    sign_contract_4,
    cancel_award_4,
    cancel_main_award_4,
    cancel_first_main_award_4,
    merge_by_two_contracts_4,
    try_merge_main_contract_4,
    try_merge_contract_two_times_4,
    activate_contract_with_complaint_4,
    additional_awards_dateSigned_4,
)


def prepare_bids(init_bids):
    """ Make different indetifier id for every bid """
    init_bids = deepcopy(init_bids)
    base_identifier_id = int(init_bids[0]['tenderers'][0]['identifier']['id'])
    for bid in init_bids:
        base_identifier_id += 1
        bid['tenderers'][0]['identifier']['id'] = "{:0=8}".format(base_identifier_id)
    return init_bids


class TenderContractResourceTest(BaseTenderUAContentWebTest):
    initial_status = 'active.qualification'
    initial_bids = test_bids

    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        # Create award
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id),
            {'data': {'suppliers': [test_organization], 'status': 'pending', 'bid_id': self.initial_bids[0]['id'],
                      'value': self.initial_bids[0]['value']}})
        award = response.json['data']
        self.award_id = award['id']
        self.award_value = award['value']
        self.app.authorization = authorization
        self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, self.award_id, self.tender_token),
            {"data": {"status": "active", "qualified": True, "eligible": True}})

    test_create_tender_contract_invalid = snitch(create_tender_contract_invalid)
    test_create_tender_contract = snitch(create_tender_contract)
    test_patch_tender_contract_datesigned = snitch(patch_tender_contract_datesigned)
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_get_tender_contract = snitch(get_tender_contract)
    test_get_tender_contracts = snitch(get_tender_contracts)


class TenderContractDocumentResourceTest(BaseTenderUAContentWebTest):
    initial_status = 'active.qualification'
    initial_bids = test_bids

    def setUp(self):
        super(TenderContractDocumentResourceTest, self).setUp()
        # Create award
        auth = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id),
            {'data': {'suppliers': [test_organization], 'status': 'pending', 'bid_id': self.initial_bids[0]['id']}})
        award = response.json['data']
        self.award_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, self.award_id),
                                       {"data": {"status": "active", "qualified": True, "eligible": True}})
        # Create contract for award
        response = self.app.post_json('/tenders/{}/contracts'.format(self.tender_id), {
            'data': {'title': 'contract title', 'description': 'contract description', 'awardID': self.award_id}})
        contract = response.json['data']
        self.contract_id = contract['id']
        self.app.authorization = auth

    test_not_found = snitch(not_found)
    test_create_tender_contract_document = snitch(create_tender_contract_document)
    test_put_tender_contract_document = snitch(put_tender_contract_document)
    test_patch_tender_contract_document = snitch(patch_tender_contract_document)


class TenderMergedContracts2LotsResourceTest(BaseTenderUAContentWebTest):
    initial_status = 'active.qualification'
    initial_bids = prepare_bids(test_bids)
    initial_lots = deepcopy(2 * test_lots)
    initial_auth = ('Basic', ('broker', ''))

    test_not_found_contract_for_award_2 = snitch(not_found_contract_for_award_2)
    test_try_merge_not_real_award_2 = snitch(try_merge_not_real_award_2)
    test_try_merge_itself_2 = snitch(try_merge_itself_2)
    test_merge_two_contracts_2 = snitch(merge_two_contracts_2)
    test_standstill_period_2 = snitch(standstill_period_2)
    test_additional_awards_dateSigned_2 = snitch(additional_awards_dateSigned_2)
    test_activate_contract_with_complaint_2 = snitch(activate_contract_with_complaint_2)
    test_cancel_award_2 = snitch(cancel_award_2)
    test_cancel_main_award_2 = snitch(cancel_main_award_2)
    test_merge_two_contracts_with_different_suppliers_id_2 = snitch(merge_two_contracts_with_different_suppliers_id_2)
    test_merge_two_contracts_with_different_suppliers_scheme_2 = snitch(
        merge_two_contracts_with_different_suppliers_scheme_2)
    test_set_big_value_2 = snitch(set_big_value_2)


class TenderMergedContracts3LotsResourceTest(BaseTenderUAContentWebTest):
    initial_status = 'active.qualification'
    initial_bids = prepare_bids(test_bids)
    initial_lots = deepcopy(3 * test_lots)
    initial_auth = ('Basic', ('broker', ''))

    test_merge_three_contracts_3 = snitch(merge_three_contracts_3)
    test_standstill_period_3 = snitch(standstill_period_3)
    test_activate_contract_with_complaint_3 = snitch(activate_contract_with_complaint_3)
    test_cancel_award_3 = snitch(cancel_award_3)
    test_cancel_main_award_3 = snitch(cancel_main_award_3)
    test_try_merge_pending_award_3 = snitch(try_merge_pending_award_3)
    test_additional_awards_dateSigned_3 = snitch(additional_awards_dateSigned_3)


class TenderMergedContracts4LotsResourceTest(BaseTenderUAContentWebTest):
    initial_status = 'active.qualification'
    initial_bids = prepare_bids(test_bids)
    initial_lots = deepcopy(4 * test_lots)
    initial_auth = ('Basic', ('broker', ''))

    test_merge_four_contracts = snitch(merge_four_contracts_4)
    test_sign_contract = snitch(sign_contract_4)
    test_cancel_award_4lot = snitch(cancel_award_4)
    test_cancel_main_award_4lot = snitch(cancel_main_award_4)
    test_cancel_first_main_award = snitch(cancel_first_main_award_4)
    test_merge_by_two_contracts = snitch(merge_by_two_contracts_4)
    test_try_merge_main_contract = snitch(try_merge_main_contract_4)
    test_try_merge_contract_two_times = snitch(try_merge_contract_two_times_4)
    test_activate_contract_with_complaint_4lot = snitch(activate_contract_with_complaint_4)
    test_additional_awards_dateSigned_4lot = snitch(additional_awards_dateSigned_4)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderMergedContracts2LotsResourceTest))
    suite.addTest(unittest.makeSuite(TenderMergedContracts3LotsResourceTest))
    suite.addTest(unittest.makeSuite(TenderMergedContracts4LotsResourceTest))

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
