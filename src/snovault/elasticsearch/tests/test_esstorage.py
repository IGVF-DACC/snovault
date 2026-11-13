import pytest
from unittest.mock import Mock, call

pytestmark = [pytest.mark.indexing]


class TestPickStorage(object):

    def test_get_rev_links_with_switched_storage(self):
        # If we have a model that was loaded from elasticsearch
        # but the datastore is now database, we need to be sure
        # to get the rev links from the database.
        from pyramid.testing import (
            DummyRequest,
            testConfig,
        )
        from ..esstorage import (
            CachedModel,
            PickStorage,
        )

        model = CachedModel({'_source': {'uuid': 'dummy'}})
        model2 = Mock()
        read = Mock()
        write = Mock()
        write.get_by_uuid.return_value = model2
        storage = PickStorage(read, write)

        request = DummyRequest()
        request.datastore = 'database'
        with testConfig(request=request):
            storage.get_rev_links(model, 'rel')

        assert write.get_rev_links.called_once
        rev_links_model = write.get_rev_links.call_args[0][0]
        assert rev_links_model is model2


def test_pick_storage_get_by_unique_key_forces_database_request_when_model_is_invalidated(dummy_request):
    from pyramid.testing import testConfig
    from ..esstorage import PickStorage
    # Uses ES when model not invalidated.
    dummy_request.datastore = 'elasticsearch'
    es_model = Mock()
    pg_model = Mock()
    read = Mock()
    write = Mock()
    read.get_by_unique_key.return_value = es_model
    write.get_by_unique_key.return_value = pg_model
    es_model.invalidated.return_value = False
    pg_model.invalidated.return_value = False
    storage = PickStorage(read, write)
    with testConfig(request=dummy_request):
        model = storage.get_by_unique_key('accession', 'SNOFL000LSQ')
    assert model is es_model
    assert dummy_request.datastore == 'elasticsearch'
    # Switches to PG when model invalidated.
    es_model.invalidated.return_value = True
    with testConfig(request=dummy_request):
        model = storage.get_by_unique_key('accession', 'SNOFL000LSQ')
    assert model is pg_model
    assert dummy_request.datastore == 'database'


def test_pick_storage_get_by_uuid_forces_database_request_when_model_is_invalidated(dummy_request):
    from pyramid.testing import testConfig
    from ..esstorage import PickStorage
    # Uses ES when model not invalidated.
    dummy_request.datastore = 'elasticsearch'
    es_model = Mock()
    pg_model = Mock()
    read = Mock()
    write = Mock()
    read.get_by_uuid.return_value = es_model
    write.get_by_uuid.return_value = pg_model
    es_model.invalidated.return_value = False
    pg_model.invalidated.return_value = False
    storage = PickStorage(read, write)
    with testConfig(request=dummy_request):
        model = storage.get_by_uuid('123')
    assert model is es_model
    assert dummy_request.datastore == 'elasticsearch'
    # Switches to PG when model invalidated.
    es_model.invalidated.return_value = True
    with testConfig(request=dummy_request):
        model = storage.get_by_uuid('123')
    assert model is pg_model
    assert dummy_request.datastore == 'database'


def test_pick_storage_get_by_unique_key_does_not_force_database_when_model_is_none(dummy_request):
    from pyramid.testing import testConfig
    from ..esstorage import PickStorage
    dummy_request.datastore = 'elasticsearch'
    es_model = Mock()
    pg_model = Mock()
    read = Mock()
    write = Mock()
    read.get_by_unique_key.return_value = es_model
    write.get_by_unique_key.return_value = pg_model
    es_model.invalidated.return_value = False
    pg_model.invalidated.return_value = False
    storage = PickStorage(read, write)
    with testConfig(request=dummy_request):
        model = storage.get_by_unique_key('accession', 'SNOFL000LSQ')
    assert model is es_model
    assert dummy_request.datastore == 'elasticsearch'
    # Set model to None.
    read.get_by_unique_key.return_value = None
    with testConfig(request=dummy_request):
        model = storage.get_by_unique_key('accession', 'SNOFL000LSQ')
    # Make sure it looks in PG and doesn't force request.
    assert model is pg_model
    assert dummy_request.datastore == 'elasticsearch'


def test_pick_storage_get_by_uuid_does_not_force_database_when_model_is_none(dummy_request):
    from pyramid.testing import testConfig
    from ..esstorage import PickStorage
    dummy_request.datastore = 'elasticsearch'
    es_model = Mock()
    pg_model = Mock()
    read = Mock()
    write = Mock()
    read.get_by_uuid.return_value = es_model
    write.get_by_uuid.return_value = pg_model
    es_model.invalidated.return_value = False
    pg_model.invalidated.return_value = False
    storage = PickStorage(read, write)
    with testConfig(request=dummy_request):
        model = storage.get_by_uuid('123')
    assert model is es_model
    assert dummy_request.datastore == 'elasticsearch'
    # Set model to None.
    read.get_by_uuid.return_value = None
    with testConfig(request=dummy_request):
        model = storage.get_by_uuid('123')
    # Make sure it looks in PG and doesn't force request.
    assert model is pg_model
    assert dummy_request.datastore == 'elasticsearch'


def test_pick_storage_get_by_uuids_batches_only_for_the_write_database(dummy_request):
    from pyramid.testing import testConfig
    from ..esstorage import PickStorage
    read = Mock()
    write = Mock()
    write.get_by_uuids.return_value = ['pg_model_1', 'pg_model_2']
    storage = PickStorage(read, write)
    # Batches on the write database.
    dummy_request.datastore = 'database'
    with testConfig(request=dummy_request):
        models = storage.get_by_uuids(['uuid_1', 'uuid_2'])
    assert models == ['pg_model_1', 'pg_model_2']
    write.get_by_uuids.assert_called_once_with(['uuid_1', 'uuid_2'])
    assert read.method_calls == []
    write.reset_mock()
    # Goes one at a time through get_by_uuid for Elasticsearch, so
    # invalidated documents can still fall back to the database.
    es_model = Mock()
    es_model.invalidated.return_value = False
    read.get_by_uuid.side_effect = [es_model, es_model]
    dummy_request.datastore = 'elasticsearch'
    with testConfig(request=dummy_request):
        models = storage.get_by_uuids(['uuid_1', 'uuid_2'])
    assert models == [es_model, es_model]
    assert [c.args for c in read.get_by_uuid.call_args_list] == [('uuid_1',), ('uuid_2',)]
    assert write.method_calls == []
    assert dummy_request.datastore == 'elasticsearch'


def test_pick_storage_get_by_unique_keys_batches_only_for_the_write_database(dummy_request):
    from pyramid.testing import testConfig
    from ..esstorage import PickStorage
    read = Mock()
    write = Mock()
    write.get_by_unique_keys.return_value = ['pg_model_1', 'pg_model_2']
    storage = PickStorage(read, write)
    # Batches on the write database. The index hint is only for Elasticsearch.
    dummy_request.datastore = 'database'
    with testConfig(request=dummy_request):
        models = storage.get_by_unique_keys('accession', ['A', 'B'], index='snowflake')
    assert models == ['pg_model_1', 'pg_model_2']
    write.get_by_unique_keys.assert_called_once_with('accession', ['A', 'B'])
    assert read.method_calls == []
    write.reset_mock()
    # Goes one at a time through get_by_unique_key for Elasticsearch,
    # keeping the index hint.
    es_model = Mock()
    es_model.invalidated.return_value = False
    read.get_by_unique_key.side_effect = [es_model, es_model]
    dummy_request.datastore = 'elasticsearch'
    with testConfig(request=dummy_request):
        models = storage.get_by_unique_keys('accession', ['A', 'B'], index='snowflake')
    assert models == [es_model, es_model]
    assert read.get_by_unique_key.call_args_list == [
        call('accession', 'A', index='snowflake'),
        call('accession', 'B', index='snowflake'),
    ]
    assert write.method_calls == []
    assert dummy_request.datastore == 'elasticsearch'


def test_pick_storage_get_incoming_links_batch_only_reads_the_write_storage(dummy_request):
      from pyramid.testing import testConfig
      from ..esstorage import PickStorage
      read = Mock()
      write = Mock()
      storage = PickStorage(read, write)
      dummy_request.datastore = 'elasticsearch'
      with testConfig(request=dummy_request):
          assert storage.get_incoming_links_batch(['uuid_a', 'uuid_b'], {'rel'}) is None
      assert read.method_calls == []
      assert write.method_calls == []
      dummy_request.datastore = 'database'
      with testConfig(request=dummy_request):
          by_target = storage.get_incoming_links_batch(['uuid_a', 'uuid_b'], {'rel'})
      assert by_target == write.get_incoming_links_batch.return_value
      write.get_incoming_links_batch.assert_called_once_with(['uuid_a', 'uuid_b'], {'rel'})
