def test_batch_upgrade(testapp, invalid_snowball):

    assert invalid_snowball['status'] == 'FLYBARGS'
    upgrade = testapp.post_json(
        '/batch_upgrade', {'batch': [invalid_snowball['uuid']]}, status=200)

    res = testapp.get(invalid_snowball['@id'])
    assert res.json['schema_version'] == '2'
    err_msg = (
        'Validation failure: /snowball/{uuid}\n'
        "status: 'FLYBARGS' is not one of "
        "['proposed', 'started', 'submitted', 'ready for review', "
        "'deleted', 'released', 'revoked', 'archived', 'replaced']"
        ''.format(
            uuid=invalid_snowball['uuid'],
        )
    )
    assert upgrade.json['results'][0] == [
        'snowball',
        invalid_snowball['uuid'],
        True,  # updated
        True,   # errors
        err_msg,
    ]


def test_batch_upgrade_multi(testapp, invalid_snowball, invalid_snowball2):

    assert invalid_snowball2['alternate_accessions'] == ['THE THING THAT SHOULD NOT BE']
    upgrade = testapp.post_json(
        '/batch_upgrade', {'batch': [invalid_snowball['uuid'], invalid_snowball2['uuid']]}, status=200)

    assert len(upgrade.json['results']) == 2
    err_msg = (
        'Validation failure: /snowball/{uuid}\n'
        "status: 'FLYBARGS' is not one of "
        "['proposed', 'started', 'submitted', 'ready for review', "
        "'deleted', 'released', 'revoked', 'archived', 'replaced']"
        ''.format(
            uuid=invalid_snowball['uuid'],
        )
    )
    assert upgrade.json['results'][0] == [
        'snowball',
        invalid_snowball['uuid'],
        True,  # updated
        True,   # errors
        err_msg,
    ]


def test_batch_upgrade_regex(testapp, invalid_award):
    assert invalid_award['name'] == 'award names cannot have spaces'
    upgrade = testapp.post_json('/batch_upgrade', {'batch': [invalid_award['uuid']]}, status=200)
    err_msg = (
        'Validation failure: /award/{uuid}\n'
        "name: 'award names cannot have spaces' "
        "does not match '^[A-Za-z0-9\\\\-]+$'"
        ''.format(
            uuid=invalid_award['uuid'],
        )
    )
    assert upgrade.json['results'][0] == [
        'award',
        invalid_award['uuid'],
        True,  # updated
        True,   # errors
        err_msg,
    ]


def test_batch_upgrade_records_transaction(testapp, registry, award, lab):
    item = {
        'award': award['uuid'],
        'lab': lab['uuid'],
        'method': 'hand-packed',
        'schema_version': '1',
        'status': 'DELETED',
    }
    response1 = testapp.post_json('/snowball/' + '?validate=false', item).json['@graph'][0]
    response2 = testapp.get(response1['@id'] + '@@raw?upgrade=false').json
    assert response2['schema_version'] == '1'
    assert response2['status'] == 'DELETED'
    registry['TRANSACTION_QUEUE'].clear()
    assert registry['TRANSACTION_QUEUE'].info()['ApproximateNumberOfMessages'] == '0'
    response3 = testapp.post_json(
        '/batch_upgrade',
        {
            'batch': [
                response1['uuid']
            ]
        }
    ).json
    assert response3['results'][0] == [
        'snowball',
        response1['uuid'],
        True,  # updated
        False,  # errors
        '',  # error message
    ]
    number_of_transaction1 = int(registry['TRANSACTION_QUEUE'].info()['ApproximateNumberOfMessages'])
    assert number_of_transaction1 >= 1, f'Upgrade not recorded as transaction. Number of transaction: {number_of_transaction1}'
    response4 = testapp.post_json(
        '/batch_upgrade',
        {
            'batch': [
                response1['uuid']
            ]
        }
    ).json
    number_of_transaction2 = int(registry['TRANSACTION_QUEUE'].info()['ApproximateNumberOfMessages'])
    assert number_of_transaction2 == number_of_transaction2, f'Null upgrade produced transaction. Number of transaction: {number_of_transaction2}'
