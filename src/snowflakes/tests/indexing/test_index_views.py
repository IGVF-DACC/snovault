import pytest

pytestmark = [pytest.mark.indexing]


def test_index_views_indexer_info_view(testapp, workbook):
    response = testapp.get('/indexer-info')
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
    }
