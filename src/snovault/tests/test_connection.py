import pytest

from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.engine import Engine


targets = [
    {'name': 'one', 'uuid': '775795d3-4410-4114-836b-8eeecf1d0c2f'},
    {'name': 'two', 'uuid': 'd6784f5e-48a1-4b40-9b11-c8aefb6e1377'},
]


@pytest.fixture(autouse=True)
def autouse_external_tx(external_tx):
    pass


@pytest.fixture
def content(testapp):
    for item in targets:
        testapp.post_json('/testing-link-targets/', item, status=201)


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
