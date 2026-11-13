import pytest

from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.engine import Engine


targets = [
    {'name': 'one', 'uuid': '775795d3-4410-4114-836b-8eeecf1d0c2f'},
    {'name': 'two', 'uuid': 'd6784f5e-48a1-4b40-9b11-c8aefb6e1377'},
]


sources = [
    {'name': 'A', 'target': targets[0]['uuid'], 'uuid': '3b7f2b0e-5d3c-4a47-9b2e-0d3c6f5a9e11'},
    {'name': 'B', 'target': targets[0]['uuid'], 'uuid': 'a1c4e9d2-7f60-4b8e-8c35-2e9d41b7f6a3'},
]


@pytest.fixture(autouse=True)
def autouse_external_tx(external_tx):
    pass


@pytest.fixture
def content(testapp):
    for item in targets:
        testapp.post_json('/testing-link-targets/', item, status=201)
    for item in sources:
        testapp.post_json('/testing-link-sources/', item, status=201)


def test_connection_item_loaded_by_unique_key_is_found_by_uuid(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    by_key = conn.get_by_unique_key('testing_link_target:name', 'one')
    assert conn.get_by_uuid(targets[0]['uuid']) is by_key


def test_connection_item_loaded_by_uuid_is_found_by_unique_key(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    by_uuid = conn.get_by_uuid(targets[0]['uuid'])
    assert conn.get_by_unique_key('testing_link_target:name', 'one') is by_uuid


def test_connection_get_by_uuids_raises_type_error_for_a_bad_type(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    with pytest.raises(TypeError):
        conn.get_by_uuids([targets[0]['uuid'], 1])


def test_connection_get_by_uuids_accepts_uuid_objects_and_default(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    one = targets[0]['uuid']
    items = conn.get_by_uuids([UUID(one), 'not-a-uuid'], default=False)
    assert items == [conn.get_by_uuid(one), False]


def test_connection_get_by_uuids_matches_get_by_uuid(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    one, two = targets[0]['uuid'], targets[1]['uuid']
    items = conn.get_by_uuids([one, 'not-a-uuid', str(uuid4()), two, one])
    assert items[0] is conn.get_by_uuid(one)
    assert items[1] is None
    assert items[2] is None
    assert items[3] is conn.get_by_uuid(two)
    assert items[4] is items[0]


def test_connection_get_by_uuids_is_one_query(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    seen = []

    def log(conn_, cursor, statement, *args):
        seen.append(statement)

    uuids = [target['uuid'] for target in targets]
    event.listen(Engine, 'before_cursor_execute', log)
    try:
        conn.get_by_uuids(uuids)
        after_first = len(seen)
        conn.get_by_uuids(uuids)
    finally:
        event.remove(Engine, 'before_cursor_execute', log)
    assert len([s for s in seen if 'FROM resources' in s]) == 1
    assert len(seen) == after_first


def test_connection_get_by_uuids_fills_the_item_cache(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    uuids = [target['uuid'] for target in targets]
    first = conn.get_by_uuids(uuids)
    assert conn.get_by_uuid(uuids[0]) is first[0]
    assert conn.get_by_uuids(uuids) == first


def test_connection_get_by_uuids_without_a_cache(content, registry):
    # No threadlocals, caches disabled.
    from snovault.interfaces import CONNECTION
    conn = registry[CONNECTION]
    uuids = [target['uuid'] for target in targets]
    items = conn.get_by_uuids(uuids)
    assert [str(item.uuid) for item in items] == uuids


def test_connection_uuid_to_path_keeps_order_and_raises_key_error(content, dummy_request, threadlocals):
    from snovault.resource_views import uuid_to_path
    dummy_request.datastore = 'database'
    one, two = targets[0]['uuid'], targets[1]['uuid']
    obj = {'links': [two, one]}
    uuid_to_path(dummy_request, obj, 'links')
    assert obj['links'] == ['/testing-link-targets/two/', '/testing-link-targets/one/']
    bad = {'links': [one, 'not-a-uuid']}
    with pytest.raises(KeyError) as excinfo:
        uuid_to_path(dummy_request, bad, 'links')
    assert excinfo.value.args == ('not-a-uuid',)
    assert bad['links'] == [one, 'not-a-uuid']
    with pytest.raises(KeyError):
        uuid_to_path(dummy_request, {'links': [str(uuid4())]}, 'links')


def test_connection_unique_key_is_cached_when_item_loads(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    one = conn.get_by_uuid(targets[0]['uuid'])
    seen = []

    def log(conn_, cursor, statement, *args):
        seen.append(statement)

    event.listen(Engine, 'before_cursor_execute', log)
    try:
        assert conn.get_by_unique_key('testing_link_target:name', 'one') is one
    finally:
        event.remove(Engine, 'before_cursor_execute', log)
    assert seen == []


def test_connection_renaming_an_item_forgets_its_old_unique_key(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    item = conn.get_by_unique_key('testing_link_target:name', 'one')
    properties = item.upgrade_properties()
    properties['name'] = 'renamed'
    item.update(properties)
    assert conn.get_by_unique_key('testing_link_target:name', 'one') is None
    assert conn.get_by_unique_key('testing_link_target:name', 'renamed') is item


def test_connection_update_without_key_changes_keeps_unique_keys(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    item = conn.get_by_unique_key('testing_link_target:name', 'one')
    properties = item.upgrade_properties()
    properties['status'] = 'deleted'
    item.update(properties)
    seen = []

    def log(conn_, cursor, statement, *args):
        seen.append(statement)

    event.listen(Engine, 'before_cursor_execute', log)
    try:
        assert conn.get_by_unique_key('testing_link_target:name', 'one') is item
    finally:
        event.remove(Engine, 'before_cursor_execute', log)
    assert seen == []


def test_connection_get_rev_links_is_one_statement(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    model = conn.get_by_uuid(targets[0]['uuid']).model
    seen = []

    def log(conn_, cursor, statement, *args):
        seen.append(statement)

    event.listen(Engine, 'before_cursor_execute', log)
    try:
        uuids = conn.get_rev_links(model, 'target', 'TestingLinkSource')
    finally:
        event.remove(Engine, 'before_cursor_execute', log)
    assert len(uuids) == len(sources)
    assert all(isinstance(uuid, UUID) for uuid in uuids)
    assert len(seen) == 1


def test_connection_cohorts_are_capped_at_a_quarter_of_the_cache():
    from snovault.connection import Connection
    from types import SimpleNamespace

    def cohort_size(settings):
        return Connection(SimpleNamespace(settings=settings)).cohort_size

    assert cohort_size({}) == 250
    assert cohort_size({'snovault.connection.rev_link_cache.capacity': '20000'}) == 500
    assert cohort_size({'snovault.connection.rev_link_cache.capacity': '2'}) == 1


def test_connection_get_rev_links_is_one_statement_per_target(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    model = conn.get_by_uuid(targets[0]['uuid']).model
    seen = []

    def log(conn_, cursor, statement, *args):
        seen.append(statement)

    event.listen(Engine, 'before_cursor_execute', log)
    try:
        reverse = conn.get_rev_links(model, 'target', 'TestingLinkSource')
        again = conn.get_rev_links(model, 'target', 'TestingLinkSource')
        untyped = conn.get_rev_links(model, 'target')
    finally:
        event.remove(Engine, 'before_cursor_execute', log)
    assert len(reverse) == len(sources)
    assert again == reverse
    assert sorted(untyped) == sorted(reverse)
    assert len(seen) == 1


def test_connection_undeclared_relations_are_read_from_storage(content, registry, dummy_request, threadlocals, mocker):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    spy = mocker.spy(conn.storage, 'get_incoming_links_batch')
    target = conn.get_by_uuid(targets[0]['uuid'])
    source = conn.get_by_uuid(sources[0]['uuid'])
    assert conn.get_rev_links(target.model, 'no_such_rel', 'TestingLinkSource') == []
    assert conn.get_rev_links(source.model, 'target', 'TestingLinkTarget') == []
    assert spy.call_count == 0
    conn.get_rev_links(target.model, 'target', 'TestingLinkSource')
    assert spy.call_count == 1


def test_connection_only_declared_relations_are_loaded(content, registry, dummy_request, threadlocals, mocker):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    spy = mocker.spy(conn.storage, 'get_incoming_links_batch')
    model = conn.get_by_uuid(targets[0]['uuid']).model
    conn.get_rev_links(model, 'target', 'TestingLinkSource')
    assert spy.call_args[0][1] == {'target'}


def test_connection_get_rev_links_falls_back_when_links_cannot_be_listed(content, registry, dummy_request, threadlocals, mocker):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    model = conn.get_by_uuid(targets[0]['uuid']).model
    expected = conn.storage.get_rev_links(model, 'target', 'testing_link_source')
    mocker.patch.object(conn.storage, 'get_incoming_links_batch', return_value=None)
    assert sorted(conn.get_rev_links(model, 'target', 'TestingLinkSource')) == sorted(expected)
    assert str(model.uuid) not in conn.rev_link_cache


def test_connection_creating_an_item_refreshes_rev_links(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION, TYPES
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    model = conn.get_by_uuid(targets[0]['uuid']).model
    before = conn.get_rev_links(model, 'target', 'TestingLinkSource')
    factory = registry[TYPES]['TestingLinkSource'].factory
    created = factory.create(registry, uuid4(), {'name': 'C', 'target': targets[0]['uuid']})
    after = conn.get_rev_links(model, 'target', 'TestingLinkSource')
    assert sorted(after) == sorted(before + [created.uuid])


def test_connection_updating_links_refreshes_rev_links(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    one = conn.get_by_uuid(targets[0]['uuid'])
    two = conn.get_by_uuid(targets[1]['uuid'])
    before_one = conn.get_rev_links(one.model, 'target', 'TestingLinkSource')
    assert conn.get_rev_links(two.model, 'target', 'TestingLinkSource') == []
    moved = conn.get_by_uuid(sources[0]['uuid'])
    properties = moved.upgrade_properties()
    properties['target'] = targets[1]['uuid']
    moved.update(properties)
    assert sorted(conn.get_rev_links(one.model, 'target', 'TestingLinkSource')
                  ) == sorted(set(before_one) - {moved.uuid})
    assert conn.get_rev_links(two.model, 'target', 'TestingLinkSource') == [moved.uuid]


def test_connection_updating_without_properties_keeps_rev_links(content, registry, dummy_request, threadlocals, mocker):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    spy = mocker.spy(conn.storage, 'get_incoming_links_batch')
    model = conn.get_by_uuid(targets[0]['uuid']).model
    conn.get_rev_links(model, 'target', 'TestingLinkSource')
    source = conn.get_by_uuid(sources[0]['uuid'])
    conn.update(source.model, None, sheets={'extra': {'a': 1}})
    conn.get_rev_links(model, 'target', 'TestingLinkSource')
    assert spy.call_count == 1


def test_batchupgrade_repair_refreshes_rev_links(content, registry, dummy_request, threadlocals):
    from snovault.batchupgrade import update_item
    from snovault.interfaces import CONNECTION, STORAGE
    from snovault.storage import Link
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    storage = registry[STORAGE].write
    two = conn.get_by_uuid(targets[1]['uuid'])
    source = conn.get_by_uuid(sources[0]['uuid'])
    # A link row that the source's own properties do not have.
    session = storage.DBSession()
    session.add(Link(source_rid=source.model.rid, rel='target', target_rid=two.model.rid))
    session.flush()
    session.expire_all()
    assert conn.get_rev_links(two.model, 'target', 'TestingLinkSource') == [source.uuid]
    update, errors = update_item(storage, source, dummy_request)
    assert update
    assert errors == []
    assert conn.get_rev_links(two.model, 'target', 'TestingLinkSource') == []
