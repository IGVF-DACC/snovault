import pytest
from unittest.mock import Mock, call


def make_connection(storage=None):
    from snovault.connection import Connection
    registry = Mock()
    conn = Connection.__new__(Connection)
    from snovault.cache import ManagerLRUCache
    conn.item_cache = ManagerLRUCache('test.item_cache', 100)
    conn.unique_key_cache = ManagerLRUCache('test.key_cache', 100)
    conn.embed_cache = ManagerLRUCache('test.embed_cache', 100)
    conn.registry = registry
    if storage is not None:
        conn.registry.__getitem__ = Mock(return_value=storage)
    return conn


def make_model(item_type, uuid_str):
    model = Mock()
    model.item_type = item_type
    model.uuid = uuid_str
    model.used_for = Mock()
    return model


def make_item(uuid_str):
    item = Mock()
    item.uuid = uuid_str
    return item


def test_get_by_uuids_returns_cached_items_without_storage_call():
    from snovault.connection import Connection
    storage = Mock()
    conn = make_connection(storage)

    item1 = make_item('uuid-1')
    item2 = make_item('uuid-2')
    conn.item_cache['uuid-1'] = item1
    conn.item_cache['uuid-2'] = item2

    results = conn.get_by_uuids(['uuid-1', 'uuid-2'])

    assert results == [item1, item2]
    storage.get_by_uuids.assert_not_called()


def test_get_by_uuids_fetches_uncached_items_in_one_batch_call():
    storage = Mock()
    conn = make_connection(storage)

    model1 = make_model('test_item', 'uuid-1')
    model2 = make_model('test_item', 'uuid-2')
    storage.get_by_uuids.return_value = [model1, model2]

    item_factory = Mock(return_value=make_item('uuid-1'))
    type_info = Mock()
    type_info.factory = item_factory
    conn.registry.__getitem__.return_value = storage

    from snovault.interfaces import TYPES
    types_mock = Mock()
    types_mock.by_item_type = {'test_item': type_info}

    def registry_getitem(key):
        from snovault.interfaces import STORAGE, TYPES as TYPES_KEY
        if key == TYPES_KEY:
            return types_mock
        return storage

    conn.registry.__getitem__ = registry_getitem

    conn.get_by_uuids(['uuid-1', 'uuid-2'])

    storage.get_by_uuids.assert_called_once_with(['uuid-1', 'uuid-2'])


def test_get_by_uuids_populates_cache_after_fetch():
    storage = Mock()
    conn = make_connection(storage)

    model = make_model('test_item', 'uuid-1')
    storage.get_by_uuids.return_value = [model]

    item = make_item('uuid-1')
    item_factory = Mock(return_value=item)
    type_info = Mock()
    type_info.factory = item_factory
    types_mock = Mock()
    types_mock.by_item_type = {'test_item': type_info}

    from snovault.interfaces import TYPES as TYPES_KEY
    def registry_getitem(key):
        if key == TYPES_KEY:
            return types_mock
        return storage
    conn.registry.__getitem__ = registry_getitem

    conn.get_by_uuids(['uuid-1'])
    # Second call should hit cache, not storage
    conn.get_by_uuids(['uuid-1'])

    assert storage.get_by_uuids.call_count == 1


def test_get_by_uuids_mixed_cache_hits_and_misses():
    storage = Mock()
    conn = make_connection(storage)

    cached_item = make_item('uuid-cached')
    conn.item_cache['uuid-cached'] = cached_item

    missing_model = make_model('test_item', 'uuid-missing')
    missing_item = make_item('uuid-missing')
    storage.get_by_uuids.return_value = [missing_model]

    item_factory = Mock(return_value=missing_item)
    type_info = Mock()
    type_info.factory = item_factory
    types_mock = Mock()
    types_mock.by_item_type = {'test_item': type_info}

    from snovault.interfaces import TYPES as TYPES_KEY
    def registry_getitem(key):
        if key == TYPES_KEY:
            return types_mock
        return storage
    conn.registry.__getitem__ = registry_getitem

    results = conn.get_by_uuids(['uuid-cached', 'uuid-missing'])

    assert results[0] is cached_item
    assert results[1] is missing_item
    # Only the missing uuid was sent to storage
    storage.get_by_uuids.assert_called_once_with(['uuid-missing'])


def test_get_by_uuids_returns_default_for_not_found():
    storage = Mock()
    conn = make_connection(storage)
    storage.get_by_uuids.return_value = [None]

    from snovault.interfaces import TYPES as TYPES_KEY
    types_mock = Mock()
    types_mock.by_item_type = {}
    def registry_getitem(key):
        if key == TYPES_KEY:
            return types_mock
        return storage
    conn.registry.__getitem__ = registry_getitem

    results = conn.get_by_uuids(['uuid-missing'], default='MISSING')

    assert results == ['MISSING']


def test_get_by_uuids_preserves_order():
    storage = Mock()
    conn = make_connection(storage)

    model_a = make_model('test_item', 'uuid-a')
    model_b = make_model('test_item', 'uuid-b')
    model_c = make_model('test_item', 'uuid-c')

    item_a = make_item('uuid-a')
    item_b = make_item('uuid-b')
    item_c = make_item('uuid-c')

    # Storage returns them in a different order than requested
    storage.get_by_uuids.return_value = [model_a, model_b, model_c]

    items_by_uuid = {'uuid-a': item_a, 'uuid-b': item_b, 'uuid-c': item_c}

    def factory(registry, model):
        return items_by_uuid[str(model.uuid)]

    type_info = Mock()
    type_info.factory = factory
    types_mock = Mock()
    types_mock.by_item_type = {'test_item': type_info}

    from snovault.interfaces import TYPES as TYPES_KEY
    def registry_getitem(key):
        if key == TYPES_KEY:
            return types_mock
        return storage
    conn.registry.__getitem__ = registry_getitem

    results = conn.get_by_uuids(['uuid-c', 'uuid-a', 'uuid-b'])

    assert results[0] is item_c
    assert results[1] is item_a
    assert results[2] is item_b


def test_get_by_uuids_empty_input():
    storage = Mock()
    conn = make_connection(storage)
    results = conn.get_by_uuids([])
    assert results == []
    storage.get_by_uuids.assert_not_called()
