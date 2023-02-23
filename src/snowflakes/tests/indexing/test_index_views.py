import pytest

pytestmark = [pytest.mark.indexing]


def test_index_views_indexer_info_view(testapp, workbook, poll_until_indexing_is_done):
    print('waiting')
    poll_until_indexing_is_done(testapp)
    print('done waiting')
    response = testapp.get('/indexer-info')
    print('response:')
    print(response.json)
    assert response.json == {
        'transaction_queue': {
            'ApproximateNumberOfMessages': 0,
            'ApproximateNumberOfMessagesNotVisible': 0,
            'ApproximateNumberOfMessagesDelayed': 0
        },
        'invalidation_queue': {
            'ApproximateNumberOfMessages': 0,
            'ApproximateNumberOfMessagesNotVisible': 0,
            'ApproximateNumberOfMessagesDelayed': 0
        },
        'is_indexing': False
    }, response.json
