import pytest

pytestmark = [pytest.mark.indexing]


def test_index_views_indexer_info_view(testapp, workbook, poll_until_indexing_is_done):
    poll_until_indexing_is_done(testapp)
    response = testapp.get('/indexer-info')
    assert response.json == {
        'transaction_queue': {
            'ApproximateNumberOfMessages': 0,
            'ApproximateNumberOfMessagesNotVisible': 0,
            'ApproximateNumberOfMessagesDelayed': 0
        },
        'transaction_dead_letter_queue': {
            'ApproximateNumberOfMessages': 0,
            'ApproximateNumberOfMessagesNotVisible': 0,
            'ApproximateNumberOfMessagesDelayed': 0
        },
        'invalidation_queue': {
            'ApproximateNumberOfMessages': 0,
            'ApproximateNumberOfMessagesNotVisible': 0,
            'ApproximateNumberOfMessagesDelayed': 0
        },
        'invalidation_dead_letter_queue': {
            'ApproximateNumberOfMessages': 0,
            'ApproximateNumberOfMessagesNotVisible': 0,
            'ApproximateNumberOfMessagesDelayed': 0
        },
        'is_indexing': False,
        'has_indexing_errors': False
    }
