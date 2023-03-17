import pytest


def test_index_views_get_approximate_numbers_from_queue():
    from snovault.elasticsearch.index_views import get_approximate_numbers_from_queue
    info = {
        'a': 'b',
        'ApproximateNumberOfMessages': '0',
        'ApproximateNumberOfMessagesDelayed': '100',
        'ApproximateNumberOfMessagesNotVisible': '32',
    }
    approximate_numbers = get_approximate_numbers_from_queue(info)
    assert approximate_numbers == {
        'ApproximateNumberOfMessages': 0,
        'ApproximateNumberOfMessagesDelayed': 100,
        'ApproximateNumberOfMessagesNotVisible': 32
    }


def test_index_views_is_indexing():
    from snovault.elasticsearch.index_views import is_indexing
    indexer_info = {
        'transaction_queue': {
            'ApproximateNumberOfMessages': 0
        },
        'invalidation_queue': {
            'ApproximateNumberOfMessages': 0
        }
    }
    assert not is_indexing(
        indexer_info
    )
    indexer_info['transaction_queue']['ApproximateNumberOfMessages'] = 33
    assert is_indexing(
        indexer_info
    )
    indexer_info['transaction_queue']['ApproximateNumberOfMessages'] = 0
    assert not is_indexing(
        indexer_info
    )
    indexer_info['invalidation_queue']['ApproximateNumberOfMessages'] = 111
    assert is_indexing(
        indexer_info
    )
    indexer_info['invalidation_queue']['ApproximateNumberOfMessages'] = 0
    assert not is_indexing(
        indexer_info
    )
    indexer_info['transaction_queue']['ApproximateNumberOfMessages'] = 103
    indexer_info['invalidation_queue']['ApproximateNumberOfMessages'] = 3534
    assert is_indexing(
        indexer_info
    )
