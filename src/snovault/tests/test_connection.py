import pytest


targets = [
    {'name': 'one', 'uuid': '775795d3-4410-4114-836b-8eeecf1d0c2f'},
]


@pytest.fixture(autouse=True)
def autouse_external_tx(external_tx):
    pass


@pytest.fixture
def content(testapp):
    for item in targets:
        testapp.post_json('/testing-link-targets/', item, status=201)


def test_item_loaded_by_unique_key_is_found_by_uuid(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    by_key = conn.get_by_unique_key('testing_link_target:name', 'one')
    assert conn.get_by_uuid(targets[0]['uuid']) is by_key


def test_item_loaded_by_uuid_is_found_by_unique_key(content, registry, dummy_request, threadlocals):
    from snovault.interfaces import CONNECTION
    dummy_request.datastore = 'database'
    conn = registry[CONNECTION]
    by_uuid = conn.get_by_uuid(targets[0]['uuid'])
    assert conn.get_by_unique_key('testing_link_target:name', 'one') is by_uuid
