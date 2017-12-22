# -*- coding: utf-8 -*-

# TenderCancellationResourceTest


def create_tender_cancellation(self):
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
        self.tender_id, self.tender_token), {'data': {'reason': 'cancellation reason'}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertIn('date', cancellation)
    self.assertEqual(cancellation['reasonType'], 'cancelled')
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], 'active.tendering')

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
        self.tender_id, self.tender_token),
        {'data': {'reason': 'cancellation reason', 'status': 'active', 'reasonType': 'unsuccessful'}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reasonType'], 'unsuccessful')
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], 'cancelled')

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
        self.tender_id, self.tender_token), {'data': {'reason': 'cancellation reason'}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't add cancellation in current (cancelled) tender status")


def patch_tender_cancellation(self):
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
        self.tender_id, self.tender_token), {'data': {'reason': 'cancellation reason'}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    old_date_status = response.json['data']['date']
    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}?acc_token={}'.format(self.tender_id, cancellation['id'], self.tender_token),
        {"data": {'reasonType': 'unsuccessful'}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["reasonType"], "unsuccessful")

    response = self.app.patch_json('/tenders/{}/cancellations/{}?acc_token={}'.format(
        self.tender_id, cancellation['id'], self.tender_token), {"data": {"status": "active"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")
    self.assertNotEqual(old_date_status, response.json['data']['date'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], 'cancelled')

    response = self.app.patch_json('/tenders/{}/cancellations/{}?acc_token={}'.format(
        self.tender_id, cancellation['id'], self.tender_token), {"data": {"status": "pending"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't update cancellation in current (cancelled) tender status")

    response = self.app.patch_json('/tenders/{}/cancellations/some_id?acc_token={}'.format(
        self.tender_id, self.tender_token), {"data": {"status": "active"}}, status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'cancellation_id'}
    ])

    response = self.app.patch_json('/tenders/some_id/cancellations/some_id', {"data": {"status": "active"}}, status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.get('/tenders/{}/cancellations/{}'.format(self.tender_id, cancellation['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")
    self.assertEqual(response.json['data']["reason"], "cancellation reason")


# TenderAwardsCancellationResourceTest


def cancellation_active_award(self):
    self.app.authorization = ('Basic', ('auction', ''))
    response = self.app.get('/tenders/{}/auction'.format(self.tender_id))
    auction_bids_data = response.json['data']['bids']
    for i in self.initial_lots:
        response = self.app.post_json('/tenders/{}/auction/{}'.format(self.tender_id, i['id']),
                                      {'data': {'bids': auction_bids_data}})

    self.app.authorization = ('Basic', ('token', ''))
    response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
    award_id = \
    [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == self.initial_lots[0]['id']][0]
    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, self.tender_token),
        {"data": {"status": "active", "qualified": True, "eligible": True}})

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                      "cancellationOf": "lot",
                                      "relatedLot": self.initial_lots[0]['id']
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])


def cancellation_unsuccessful_award(self):
    self.app.authorization = ('Basic', ('auction', ''))
    response = self.app.get('/tenders/{}/auction'.format(self.tender_id))
    auction_bids_data = response.json['data']['bids']
    for i in self.initial_lots:
        response = self.app.post_json('/tenders/{}/auction/{}'.format(self.tender_id, i['id']),
                                      {'data': {'bids': auction_bids_data}})

    self.app.authorization = ('Basic', ('token', ''))
    response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
    award_id = \
    [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == self.initial_lots[0]['id']][0]
    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, self.tender_token),
        {"data": {"status": "unsuccessful"}})

    response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
    award_id = \
    [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == self.initial_lots[0]['id']][0]
    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, award_id, self.tender_token),
        {"data": {"status": "unsuccessful"}})

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                      "cancellationOf": "lot",
                                      "relatedLot": self.initial_lots[0]['id']
                                  }}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"], "Can't add cancellation if all awards is unsuccessful")

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                  }}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"], "Can't add cancellation if all awards is unsuccessful")

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                      "cancellationOf": "lot",
                                      "relatedLot": self.initial_lots[1]['id']
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])


# TenderLotCancellationResourceTest


def create_tender_lot_cancellation(self):
    lot_id = self.initial_lots[0]['id']
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'active')
    self.assertEqual(response.json['data']["status"], 'active.tendering')

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'cancelled')
    self.assertEqual(response.json['data']["status"], 'cancelled')

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
        self.tender_id, self.tender_token), {'data': {'reason': 'cancellation reason'}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't add cancellation in current (cancelled) tender status")


def patch_tender_lot_cancellation(self):
    lot_id = self.initial_lots[0]['id']
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']

    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}?acc_token={}'.format(self.tender_id, cancellation['id'], self.tender_token),
        {"data": {"status": "active"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'cancelled')
    self.assertEqual(response.json['data']["status"], 'cancelled')

    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}?acc_token={}'.format(self.tender_id, cancellation['id'], self.tender_token),
        {"data": {"status": "pending"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't update cancellation in current (cancelled) tender status")

    response = self.app.get('/tenders/{}/cancellations/{}'.format(self.tender_id, cancellation['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")
    self.assertEqual(response.json['data']["reason"], "cancellation reason")


# TenderLotsCancellationResourceTest


def create_tender_lots_cancellation(self):
    lot_id = self.initial_lots[0]['id']
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'active')
    self.assertEqual(response.json['data']["status"], 'active.tendering')

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'cancelled')
    self.assertNotEqual(response.json['data']["status"], 'cancelled')

    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      'status': 'active',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"], "Can add cancellation only in active lot status")

    response = self.app.post_json(
        '/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token), {'data': {
            'reason': 'cancellation reason',
            'status': 'active',
            "cancellationOf": "lot",
            "relatedLot": self.initial_lots[1]['id']
        }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']
    self.assertEqual(cancellation['reason'], 'cancellation reason')
    self.assertEqual(cancellation['status'], 'active')
    self.assertIn('id', cancellation)
    self.assertIn(cancellation['id'], response.headers['Location'])

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'cancelled')
    self.assertEqual(response.json['data']['lots'][1]["status"], 'cancelled')
    self.assertEqual(response.json['data']["status"], 'cancelled')


def patch_tender_lots_cancellation(self):
    lot_id = self.initial_lots[0]['id']
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': {
                                      'reason': 'cancellation reason',
                                      "cancellationOf": "lot",
                                      "relatedLot": lot_id
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    cancellation = response.json['data']

    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}?acc_token={}'.format(self.tender_id, cancellation['id'], self.tender_token),
        {"data": {"status": "active"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['lots'][0]["status"], 'cancelled')
    self.assertNotEqual(response.json['data']["status"], 'cancelled')

    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}?acc_token={}'.format(self.tender_id, cancellation['id'], self.tender_token),
        {"data": {"status": "pending"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"], "Can update cancellation only in active lot status")

    response = self.app.get('/tenders/{}/cancellations/{}'.format(self.tender_id, cancellation['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")
    self.assertEqual(response.json['data']["reason"], "cancellation reason")


# TenderLotCancellationContractTest

def create_lot_cancellation_on_merged_contract(self):
    second_lot_id = self.initial_lots[1]['id']

    # Create awards
    self.app.authorization = ('Basic', ('token', ''))
    request_path = '/tenders/{}/awards'.format(self.tender_id)
    response = self.app.post_json(request_path, {'data': {'suppliers': [self.test_organization], 'status': u'pending',
                                                          'bid_id': self.initial_bids[0]['id'],
                                                          'lotID': self.initial_lots[0]['id'],
                                                          "value": {"amount": 500}}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    first_award = response.json['data']
    response = self.app.post_json(request_path, {'data': {'suppliers': [self.test_organization], 'status': u'pending',
                                                          'bid_id': self.initial_bids[1]['id'],
                                                          'lotID': self.initial_lots[1]['id'],
                                                          "value": {"amount": 500}}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    second_award = response.json['data']
    response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, first_award['id']),
                                   {"data": {"status": "active"}})
    self.assertEqual(response.json['data']['status'], 'active')
    response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, second_award['id']),
                                   {"data": {"status": "active"}})
    self.assertEqual(response.json['data']['status'], 'active')

    # Merge contract
    response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
    response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
        self.tender_id, response.json['data'][0]['id'], self.tender_token),
        {"data": {"additionalAwardIDs": [response.json['data'][1]['awardID']]}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')

    # Create cancellation on lot
    response = self.app.post_json('/tenders/{}/cancellations'.format(self.tender_id),
                                  {"data": {
                                      "reason": "cancellation reason",
                                      "cancellationOf": "lot",
                                      "relatedLot": second_lot_id}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can add cancellation on lot if corresponding contract is merged.")


def create_cancellation_on_lot_with_cancelled_awards(self):
    """ Try create cancellation when we already have cancelled award """
    # Create awards
    self.app.authorization = ('Basic', ('token', ''))
    request_path = '/tenders/{}/awards'.format(self.tender_id)
    response = self.app.post_json(request_path, {'data': {'suppliers': [self.test_organization],
                                                          'status': u'pending',
                                                          'bid_id': self.initial_bids[0]['id'],
                                                          'lotID': self.initial_lots[0]['id'],
                                                          'value': {"amount": 500}}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    first_award = response.json['data']
    response = self.app.post_json(request_path, {'data': {'suppliers': [self.test_organization],
                                                          'status': u'pending',
                                                          'bid_id': self.initial_bids[1]['id'],
                                                          'lotID': self.initial_lots[1]['id'],
                                                          "value": {"amount": 500}}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    second_award = response.json['data']
    response = self.app.patch_json(
        '/tenders/{}/awards/{}'.format(self.tender_id, first_award['id']),
        {"data": {"status": "active"}})
    self.assertEqual(response.json['data']['status'], 'active')
    response = self.app.patch_json(
        '/tenders/{}/awards/{}'.format(self.tender_id, second_award['id']),
        {"data": {"status": "active"}})
    self.assertEqual(response.json['data']['status'], 'active')

    # Cancel first award
    response = self.app.patch_json(
        '/tenders/{}/awards/{}'.format(self.tender_id, first_award['id']),
        {"data": {"status": "cancelled"}})
    self.assertEqual(response.json['data']['status'], 'cancelled')

    # Check number awards
    awards = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))
    self.assertEqual(len(awards.json['data']), 3)

    # Get new award
    new_awards = [award for award in awards.json['data']
                  if award['lotID'] == self.initial_lots[0]['id']
                  and award['status'] == 'pending']
    self.assertEqual(len(new_awards), 1)
    new_award = new_awards[0]

    # Active and merge new award
    response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
        self.tender_id, new_award['id'], self.tender_token),
        {'data': {'status': 'active'}})
    third_award = response.json['data']

    response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
    second_contract = [c for c in response.json['data'] if c['awardID'] == second_award['id']][0]
    response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
        self.tender_id, second_contract['id'], self.tender_token),
        {"data": {"additionalAwardIDs": [third_award['id']]}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')

    # Create cancellation on lot
    response = self.app.post_json('/tenders/{}/cancellations'.format(self.tender_id),
                                  {"data": {"reason": "cancellation reason",
                                            "cancellationOf": "lot",
                                            "relatedLot": third_award['lotID']}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can add cancellation on lot if corresponding contract is merged.")


def update_lot_cancellation_on_merged_contract(self):
    second_lot_id = self.initial_lots[1]['id']

    # Create awards
    self.app.authorization = ('Basic', ('token', ''))
    request_path = '/tenders/{}/awards'.format(self.tender_id)
    response = self.app.post_json(request_path, {'data': {'suppliers': [self.test_organization], 'status': u'pending',
                                                          'bid_id': self.initial_bids[0]['id'],
                                                          'lotID': self.initial_lots[0]['id'],
                                                          "value": {"amount": 500}}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    first_award = response.json['data']
    response = self.app.post_json(request_path, {'data': {'suppliers': [self.test_organization], 'status': u'pending',
                                                          'bid_id': self.initial_bids[1]['id'],
                                                          'lotID': self.initial_lots[1]['id'],
                                                          "value": {"amount": 500}}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    second_award = response.json['data']
    response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, first_award['id']),
                                   {"data": {"status": "active"}})
    self.assertEqual(response.json['data']['status'], 'active')
    response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, second_award['id']),
                                   {"data": {"status": "active"}})
    self.assertEqual(response.json['data']['status'], 'active')

    # Create cancellation on lot
    response = self.app.post_json('/tenders/{}/cancellations'.format(self.tender_id),
                                  {"data": {'reason': 'cancellation reason',
                                            "cancellationOf": "lot",
                                            "relatedLot": second_lot_id}})
    self.assertEqual(response.status, '201 Created')
    cancellation = response.json['data']

    # Merge contract
    response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
    response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
        self.tender_id, response.json['data'][0]['id'], self.tender_token),
        {"data": {"additionalAwardIDs": [response.json['data'][1]['awardID']]}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')

    # Activate cancellation on lot
    response = self.app.patch_json('/tenders/{}/cancellations/{}'.format(self.tender_id, cancellation['id']),
                                   {'data': {"status": "active"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can update cancellation on lot if corresponding contract is merged.")


# TenderCancellationDocumentResourceTest


def not_found(self):
    response = self.app.post('/tenders/some_id/cancellations/some_id/documents', status=404, upload_files=[
        ('file', 'name.doc', 'content')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.post(
        '/tenders/{}/cancellations/some_id/documents?acc_token={}'.format(self.tender_id, self.tender_token),
        status=404, upload_files=[('file', 'name.doc', 'content')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'cancellation_id'}
    ])

    response = self.app.post(
        '/tenders/{}/cancellations/{}/documents?acc_token={}'.format(self.tender_id, self.cancellation_id,
                                                                     self.tender_token), status=404, upload_files=[
            ('invalid_value', 'name.doc', 'content')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'body', u'name': u'file'}
    ])

    response = self.app.get('/tenders/some_id/cancellations/some_id/documents', status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.get('/tenders/{}/cancellations/some_id/documents'.format(self.tender_id), status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'cancellation_id'}
    ])

    response = self.app.get('/tenders/some_id/cancellations/some_id/documents/some_id', status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.get('/tenders/{}/cancellations/some_id/documents/some_id'.format(self.tender_id), status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'cancellation_id'}
    ])

    response = self.app.get(
        '/tenders/{}/cancellations/{}/documents/some_id'.format(self.tender_id, self.cancellation_id), status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'document_id'}
    ])

    response = self.app.put('/tenders/some_id/cancellations/some_id/documents/some_id', status=404,
                            upload_files=[('file', 'name.doc', 'content2')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.put(
        '/tenders/{}/cancellations/some_id/documents/some_id?acc_token={}'.format(self.tender_id, self.tender_token),
        status=404, upload_files=[
            ('file', 'name.doc', 'content2')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'cancellation_id'}
    ])

    response = self.app.put('/tenders/{}/cancellations/{}/documents/some_id?acc_token={}'.format(
        self.tender_id, self.cancellation_id, self.tender_token), status=404,
        upload_files=[('file', 'name.doc', 'content2')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location': u'url', u'name': u'document_id'}
    ])


def create_tender_cancellation_document(self):
    response = self.app.post('/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
        self.tender_id, self.cancellation_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')])
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    doc_id = response.json["data"]['id']
    self.assertIn(doc_id, response.headers['Location'])
    self.assertEqual('name.doc', response.json["data"]["title"])
    key = response.json["data"]["url"].split('?')[-1]

    response = self.app.get(
        '/tenders/{}/cancellations/{}/documents?acc_token={}'.format(self.tender_id, self.cancellation_id,
                                                                     self.tender_token))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"][0]["id"])
    self.assertEqual('name.doc', response.json["data"][0]["title"])

    response = self.app.get(
        '/tenders/{}/cancellations/{}/documents?all=true'.format(self.tender_id, self.cancellation_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"][0]["id"])
    self.assertEqual('name.doc', response.json["data"][0]["title"])

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}?download=some_id'.format(
        self.tender_id, self.cancellation_id, doc_id), status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location': u'url', u'name': u'download'}
    ])

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}?{}'.format(
        self.tender_id, self.cancellation_id, doc_id, key))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/msword')
    self.assertEqual(response.content_length, 7)
    self.assertEqual(response.body, 'content')

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}'.format(
        self.tender_id, self.cancellation_id, doc_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"]["id"])
    self.assertEqual('name.doc', response.json["data"]["title"])

    self.set_status('complete')

    response = self.app.post('/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
        self.tender_id, self.cancellation_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')],
        status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't add document in current (complete) tender status")


def put_tender_cancellation_document(self):
    response = self.app.post('/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
        self.tender_id, self.cancellation_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')])
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    doc_id = response.json["data"]['id']
    self.assertIn(doc_id, response.headers['Location'])

    response = self.app.put(
        '/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(self.tender_id, self.cancellation_id, doc_id,
                                                                        self.tender_token),
        status=404,
        upload_files=[('invalid_name', 'name.doc', 'content')])
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'body', u'name': u'file'}
    ])

    response = self.app.put('/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(
        self.tender_id, self.cancellation_id, doc_id, self.tender_token),
        upload_files=[('file', 'name.doc', 'content2')])
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"]["id"])
    key = response.json["data"]["url"].split('?')[-1]

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}?{}'.format(
        self.tender_id, self.cancellation_id, doc_id, key))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/msword')
    self.assertEqual(response.content_length, 8)
    self.assertEqual(response.body, 'content2')

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}'.format(
        self.tender_id, self.cancellation_id, doc_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"]["id"])
    self.assertEqual('name.doc', response.json["data"]["title"])

    response = self.app.put('/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(
        self.tender_id, self.cancellation_id, doc_id, self.tender_token), 'content3', content_type='application/msword')
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"]["id"])
    key = response.json["data"]["url"].split('?')[-1]

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}?{}'.format(
        self.tender_id, self.cancellation_id, doc_id, key))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/msword')
    self.assertEqual(response.content_length, 8)
    self.assertEqual(response.body, 'content3')

    self.set_status('complete')

    response = self.app.put('/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(
        self.tender_id, self.cancellation_id, doc_id, self.tender_token),
        upload_files=[('file', 'name.doc', 'content3')], status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't update document in current (complete) tender status")


def patch_tender_cancellation_document(self):
    response = self.app.post('/tenders/{}/cancellations/{}/documents?acc_token={}'.format(
        self.tender_id, self.cancellation_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')])
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    doc_id = response.json["data"]['id']
    self.assertIn(doc_id, response.headers['Location'])

    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(self.tender_id, self.cancellation_id, doc_id,
                                                                        self.tender_token),
        {"data": {"description": "document description"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"]["id"])

    response = self.app.get('/tenders/{}/cancellations/{}/documents/{}'.format(
        self.tender_id, self.cancellation_id, doc_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(doc_id, response.json["data"]["id"])
    self.assertEqual('document description', response.json["data"]["description"])

    self.set_status('complete')

    response = self.app.patch_json(
        '/tenders/{}/cancellations/{}/documents/{}?acc_token={}'.format(self.tender_id, self.cancellation_id, doc_id,
                                                                        self.tender_token),
        {"data": {"description": "document description"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't update document in current (complete) tender status")
