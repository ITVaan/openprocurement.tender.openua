# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.tests.base import snitch

from openprocurement.tender.belowthreshold.tests.base import test_lots, test_organization
from openprocurement.tender.belowthreshold.tests.cancellation import (
    TenderCancellationResourceTestMixin,
    TenderCancellationDocumentResourceTestMixin
)
from openprocurement.tender.belowthreshold.tests.cancellation_blanks import (
    # TenderCancellationResourceTest
    create_tender_cancellation,
    patch_tender_cancellation,
    # TenderLotCancellationResourceTest
    create_tender_lot_cancellation,
    patch_tender_lot_cancellation,
    # TenderLotsCancellationResourceTest
    create_tender_lots_cancellation,
    patch_tender_lots_cancellation,
    # TenderLotCancellationContractTest
    create_lot_cancellation_on_merged_contract,
    create_cancellation_on_lot_with_cancelled_awards,
    update_lot_cancellation_on_merged_contract)

from openprocurement.tender.openua.tests.base import (
    BaseTenderUAContentWebTest, test_bids
)
from openprocurement.tender.openua.tests.cancellation_blanks import (
    # TenderAwardsCancellationResourceTest
    cancellation_active_award,
    cancellation_unsuccessful_award,
    # TenderCancellationResourceTest
    create_tender_cancellation,
    patch_tender_cancellation,
)


class TenderCancellationResourceTest(BaseTenderUAContentWebTest, TenderCancellationResourceTestMixin):
    test_create_tender_cancellation = snitch(create_tender_cancellation)
    test_patch_tender_cancellation = snitch(patch_tender_cancellation)


class TenderLotCancellationResourceTest(BaseTenderUAContentWebTest):
    initial_lots = test_lots

    test_create_tender_lot_cancellation = snitch(create_tender_lot_cancellation)
    test_patch_tender_lot_cancellation = snitch(patch_tender_lot_cancellation)


class TenderLotCancellationContractTest(BaseTenderUAContentWebTest):
    initial_status = 'active.qualification'
    initial_lots = 2 * test_lots
    initial_bids = test_bids
    test_organization = test_organization

    create_lot_cancellation_on_merged_contract = snitch(create_lot_cancellation_on_merged_contract)
    create_cancellation_on_lot_with_cancelled_awards = snitch(create_cancellation_on_lot_with_cancelled_awards)
    update_lot_cancellation_on_merged_contract = snitch(update_lot_cancellation_on_merged_contract)


class TenderLotsCancellationResourceTest(BaseTenderUAContentWebTest):
    initial_lots = 2 * test_lots

    test_create_tender_lots_cancellation = snitch(create_tender_lots_cancellation)
    test_patch_tender_lots_cancellation = snitch(patch_tender_lots_cancellation)


class TenderAwardsCancellationResourceTest(BaseTenderUAContentWebTest):
    initial_lots = 2 * test_lots
    initial_status = 'active.auction'
    initial_bids = test_bids

    test_cancellation_active_award = snitch(cancellation_active_award)
    test_cancellation_unsuccessful_award = snitch(cancellation_unsuccessful_award)


class TenderCancellationDocumentResourceTest(BaseTenderUAContentWebTest, TenderCancellationDocumentResourceTestMixin):
    def setUp(self):
        super(TenderCancellationDocumentResourceTest, self).setUp()
        # Create cancellation
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'reason': 'cancellation reason'}})
        cancellation = response.json['data']
        self.cancellation_id = cancellation['id']


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderCancellationDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderCancellationResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
