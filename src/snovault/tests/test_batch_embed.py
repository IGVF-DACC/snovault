import json

import pytest
from uuid import uuid4

N_SOURCES = 7
CACHE_NAMES = (
    'snovault.connection.embed_cache',
    'snovault.connection.item_cache',
    'snovault.connection.key_cache',
    'snovault.connection.rev_link_cache',
)


@pytest.fixture(autouse=True)
def autouse_external_tx(external_tx):
    pass


@pytest.fixture
def many_targets_and_sources(testapp):
    uuids = {}
    for prefix in ('testing-link', 'testing-custom-embed'):
        uuids[f'{prefix}-targets'] = {}
        for name in ('one', 'two'):
            res = testapp.post_json(f'/{prefix}-targets/', {'name': name}, status=201)
            uuids[f'{prefix}-targets'][name] = res.json['@graph'][0]['uuid']
        uuids[f'{prefix}-sources'] = []
        for i in range(N_SOURCES):
            res = testapp.post_json(
                f'/{prefix}-sources/',
                {
                    'name': f'S{i}',
                    'target': 'two' if i == N_SOURCES - 1 else 'one',
                    'status': 'deleted' if i == 3 else 'current',
                },
                status=201,
            )
            uuids[f'{prefix}-sources'].append(res.json['@graph'][0]['uuid'])
    return uuids


def reset_caches(threadlocals):
    for name in CACHE_NAMES:
        threadlocals.pop(name, None)


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(member) for key, member in value.items()}
    if isinstance(value, list):
        return sorted((normalize(member) for member in value), key=lambda m: json.dumps(m, sort_keys=True))
    return value


def get_json(testapp, url, batch_embed):
    return testapp.get(f'{url}&datastore=database&batch_embed={str(batch_embed).lower()}').json


@pytest.mark.parametrize('url', [
    '/testing-link-targets/one/?frame=object',
    '/testing-link-targets/one/?frame=object&skip_calculated=true',
    '/testing-link-targets/one/?frame=embedded',
    '/testing-link-targets/two/?frame=embedded',
    '/testing-link-targets/one/?frame=page',
    '/testing-custom-embed-targets/one/?frame=object',
    '/testing-custom-embed-targets/one/?frame=embedded',
    '/testing-custom-embed-targets/two/?frame=embedded',
    '/testing-custom-embed-targets/one/?frame=page',
])
def test_rendering_identical_with_and_without_batch_embed(testapp, many_targets_and_sources, url):
    batched = get_json(testapp, url, True)
    unbatched = get_json(testapp, url, False)
    assert normalize(batched) == normalize(unbatched)
    if 'frame=embedded' in url:
        assert all(isinstance(member, dict) for member in batched['reverse'])


def test_source_rendering_identical_with_and_without_batch_embed(testapp, many_targets_and_sources):
    for uuid in many_targets_and_sources['testing-link-sources']:
        url = f'/testing-link-sources/{uuid}/?frame=object'
        assert normalize(get_json(testapp, url, True)) == normalize(get_json(testapp, url, False))


def test_expand_identical_with_and_without_batch_embed(
    dummy_request, threadlocals, many_targets_and_sources
):
    results = {}
    for batch_embed in (False, True):
        reset_caches(threadlocals)
        dummy_request.batch_embed = batch_embed
        results[batch_embed] = dummy_request.embed(
            '/testing-link-targets/one/', '@@expand?expand=reverse'
        )
    assert normalize(results[True]) == normalize(results[False])
    assert len(results[True]['reverse']) == N_SOURCES - 2
    assert all(isinstance(member, dict) for member in results[True]['reverse'])


def test_path_expand_identical_with_and_without_batch_embed(
    dummy_request, threadlocals, many_targets_and_sources
):
    from snovault.util import Path
    results = {}
    for batch_embed in (False, True):
        reset_caches(threadlocals)
        dummy_request.batch_embed = batch_embed
        properties = {
            'targets': [
                '/testing-custom-embed-targets/one/',
                '/testing-custom-embed-targets/two/',
            ]
        }
        for path in ('targets', 'targets.reverse'):
            p = Path(path)
            p.expand_path_with_frame(dummy_request, properties, p.path, p.frame)
        results[batch_embed] = properties
    assert normalize(results[True]) == normalize(results[False])
    assert all(isinstance(member, dict) for member in results[True]['targets'][0]['reverse'])


def test_batch_embed_defaults_on(dummy_request):
    assert dummy_request.batch_embed is True


def test_warming_follows_batch_embed_request_param(testapp, many_targets_and_sources, mocker):
    from snovault.connection import Connection
    spy = mocker.spy(Connection, 'warm_cache_for_paths')
    url = '/testing-custom-embed-targets/one/?frame=embedded&datastore=database'
    testapp.get(url + '&batch_embed=false')
    assert spy.call_count == 0
    testapp.get(url)
    assert spy.call_count > 0
    spy.reset_mock()
    testapp.get(url + '&batch_embed=true')
    assert spy.call_count > 0


def test_get_by_uuids_matches_get_by_uuid(
    dummy_request, threadlocals, registry, many_targets_and_sources
):
    from snovault.interfaces import CONNECTION
    conn = registry[CONNECTION]
    uuids = many_targets_and_sources['testing-link-sources'] + [str(uuid4()), 'not-a-uuid']
    reset_caches(threadlocals)
    expected = [conn.get_by_uuid(u) for u in uuids]
    reset_caches(threadlocals)
    actual = conn.get_by_uuids(uuids)
    assert [a.uuid if a else None for a in actual] == [e.uuid if e else None for e in expected]
    assert actual[-2:] == [None, None]
    assert conn.get_by_uuids([]) == []


def test_warm_cache_for_paths_skips_entries_already_warm(
    dummy_request, threadlocals, registry, many_targets_and_sources, mocker
):
    from snovault.interfaces import CONNECTION
    from snovault.storage import RDBStorage
    conn = registry[CONNECTION]
    uuid_spy = mocker.spy(RDBStorage, 'get_by_uuids')
    key_spy = mocker.spy(RDBStorage, 'get_by_unique_keys')
    paths = [
        f'/testing-link-sources/{uuid}/'
        for uuid in many_targets_and_sources['testing-link-sources']
    ] + [
        '/testing-link-targets/one/',
        '/testing-link-targets/two/',
        '/testing-link-targets/missing/',
        '/not-a-collection/x/',
    ]
    reset_caches(threadlocals)
    conn.warm_cache_for_paths(paths)
    assert uuid_spy.call_count == 1
    assert key_spy.call_count == 1
    conn.warm_cache_for_paths(paths[:-2])
    assert uuid_spy.call_count == 1
    assert key_spy.call_count == 1
    assert conn.get_by_unique_key('testing_link_target:name', 'one') is not None


def test_loading_by_uuid_registers_unique_keys_only_when_batching(
    dummy_request, threadlocals, registry, many_targets_and_sources
):
    from snovault.interfaces import CONNECTION
    conn = registry[CONNECTION]
    uuid = many_targets_and_sources['testing-link-targets']['one']
    for batch_embed in (False, True):
        reset_caches(threadlocals)
        dummy_request.batch_embed = batch_embed
        conn.get_by_uuid(uuid)
        assert (('testing_link_target:name', 'one') in conn.unique_key_cache) is batch_embed


def test_item_loaded_by_uuid_is_not_requeried_by_unique_key(
    dummy_request, threadlocals, registry, many_targets_and_sources, mocker
):
    from snovault.interfaces import CONNECTION
    from snovault.storage import RDBStorage
    conn = registry[CONNECTION]
    uuid = many_targets_and_sources['testing-link-targets']['one']
    spy = mocker.spy(RDBStorage, 'get_by_unique_key')
    for batch_embed, expected_queries in ((False, 1), (True, 0)):
        reset_caches(threadlocals)
        dummy_request.batch_embed = batch_embed
        spy.reset_mock()
        conn.get_by_uuid(uuid)
        item = conn.get_by_unique_key('testing_link_target:name', 'one')
        assert str(item.uuid) == uuid
        assert spy.call_count == expected_queries


def test_rev_links_cost_one_query_per_item_and_match_in_both_modes(
    dummy_request, threadlocals, registry, many_targets_and_sources, mocker
):
    from snovault.interfaces import CONNECTION
    from snovault.storage import RDBStorage
    conn = registry[CONNECTION]
    incoming_spy = mocker.spy(RDBStorage, 'get_incoming_links')
    list_spy = mocker.spy(RDBStorage, 'get_rev_links')
    results = {}
    for batch_embed in (False, True):
        reset_caches(threadlocals)
        dummy_request.batch_embed = batch_embed
        incoming_spy.reset_mock()
        list_spy.reset_mock()
        model = conn.get_by_uuid(many_targets_and_sources['testing-link-targets']['one']).model
        first = conn.get_rev_links(model, 'target', 'TestingLinkSource')
        second = conn.get_rev_links(model, 'target', 'TestingLinkSource')
        other_rel = conn.get_rev_links(model, 'no_such_rel', 'TestingLinkSource')
        no_types = conn.get_rev_links(model, 'target')
        assert sorted(map(str, first)) == sorted(map(str, second)) == sorted(map(str, no_types))
        assert other_rel == []
        assert incoming_spy.call_count == (1 if batch_embed else 0)
        assert list_spy.call_count == (0 if batch_embed else 4)
        results[batch_embed] = sorted(map(str, first))
    assert results[True] == results[False]
    assert len(results[True]) == N_SOURCES - 1


def test_updating_links_invalidates_rev_link_memo(
    dummy_request, threadlocals, registry, many_targets_and_sources
):
    from snovault.interfaces import CONNECTION
    conn = registry[CONNECTION]
    reset_caches(threadlocals)
    dummy_request.batch_embed = True
    targets = many_targets_and_sources['testing-link-targets']
    moved = many_targets_and_sources['testing-link-sources'][0]
    two = conn.get_by_uuid(targets['two']).model
    before = {str(u) for u in conn.get_rev_links(two, 'target', 'TestingLinkSource')}
    assert moved not in before
    source = conn.get_by_uuid(moved)
    properties = source.upgrade_properties()
    properties['target'] = targets['two']
    source.update(properties)
    after = {str(u) for u in conn.get_rev_links(two, 'target', 'TestingLinkSource')}
    assert after == before | {moved}


def test_unique_keys_failure_does_not_break_loading_or_updates(
    dummy_request, threadlocals, registry, many_targets_and_sources, monkeypatch
):
    from snovault.interfaces import CONNECTION
    from snovault.tests.testing_views import TestingLinkTarget
    conn = registry[CONNECTION]
    uuid = many_targets_and_sources['testing-link-targets']['one']

    def broken(self, properties):
        raise KeyError('strain')

    monkeypatch.setattr(TestingLinkTarget, 'unique_keys', broken)
    reset_caches(threadlocals)
    dummy_request.batch_embed = True
    item = conn.get_by_uuid(uuid)
    assert str(item.uuid) == uuid
    assert ('testing_link_target:name', 'one') not in conn.unique_key_cache
    conn._forget_stale_entries(item.model, {'testing_link_target:name': ['one']}, {})


def test_upgraded_properties_is_a_cached_read_only_view_only_when_batching(
    dummy_request, threadlocals, registry, many_targets_and_sources
):
    from snovault.interfaces import CONNECTION
    conn = registry[CONNECTION]
    uuid = many_targets_and_sources['testing-link-sources'][0]
    for batch_embed in (False, True):
        reset_caches(threadlocals)
        dummy_request.batch_embed = batch_embed
        item = conn.get_by_uuid(uuid)
        first = item.upgraded_properties()
        second = item.upgraded_properties()
        assert first == item.upgrade_properties()
        assert (first is second) is batch_embed
        assert item.upgrade_properties() is not item.upgrade_properties()


def test_upgraded_properties_refresh_after_update(
    dummy_request, threadlocals, registry, many_targets_and_sources
):
    from snovault.interfaces import CONNECTION
    conn = registry[CONNECTION]
    reset_caches(threadlocals)
    dummy_request.batch_embed = True
    item = conn.get_by_uuid(many_targets_and_sources['testing-link-sources'][0])
    before = item.upgraded_properties()
    assert before['status'] == 'current'
    properties = item.upgrade_properties()
    properties['status'] = 'deleted'
    item.update(properties)
    after = item.upgraded_properties()
    assert after['status'] == 'deleted'
    assert before['status'] == 'current'


def test_items_loaded_together_get_their_rev_links_in_one_query(
    dummy_request, threadlocals, registry, many_targets_and_sources, mocker
):
    from snovault.interfaces import CONNECTION
    from snovault.storage import RDBStorage
    conn = registry[CONNECTION]
    targets = many_targets_and_sources['testing-link-targets']
    batch_spy = mocker.spy(RDBStorage, 'get_incoming_links_batch')
    single_spy = mocker.spy(RDBStorage, 'get_incoming_links')
    results = {}
    for batch_embed in (False, True):
        for load in ('uuids', 'paths'):
            reset_caches(threadlocals)
            dummy_request.batch_embed = batch_embed
            batch_spy.reset_mock()
            single_spy.reset_mock()
            if load == 'uuids':
                one, two = conn.get_by_uuids([targets['one'], targets['two']])
            else:
                conn.warm_cache_for_paths(['/testing-link-targets/one/', '/testing-link-targets/two/'])
                one, two = conn.get_by_uuid(targets['one']), conn.get_by_uuid(targets['two'])
            rev_one = conn.get_rev_links(one.model, 'target', 'TestingLinkSource')
            rev_two = conn.get_rev_links(two.model, 'target', 'TestingLinkSource')
            assert batch_spy.call_count == (1 if batch_embed else 0), (batch_embed, load)
            assert single_spy.call_count == 0
            results[(batch_embed, load)] = (sorted(map(str, rev_one)), sorted(map(str, rev_two)))
    assert len(set(map(str, results.values()))) == 1
    assert len(results[(True, 'uuids')][0]) == N_SOURCES - 1
    assert len(results[(True, 'uuids')][1]) == 1


def test_server_default_is_not_computed_for_a_value_that_is_present(
    dummy_request, threadlocals, monkeypatch
):
    from snovault.schema_utils import SERVER_DEFAULTS, validate
    calls = []

    def counting(instance, subschema):
        calls.append(1)
        return 'generated'

    monkeypatch.setitem(SERVER_DEFAULTS, 'counting', counting)
    schema = {
        'type': 'object',
        'properties': {'a': {'type': 'string', 'serverDefault': 'counting'}},
    }
    for batch_embed in (False, True):
        dummy_request.batch_embed = batch_embed
        calls.clear()
        validated, errors = validate(schema, {'a': 'given'})
        assert validated == {'a': 'given'} and not errors
        assert len(calls) == (0 if batch_embed else 1)
        calls.clear()
        validated, errors = validate(schema, {})
        assert validated == {'a': 'generated'} and len(calls) == 1


def test_stored_data_validator_skips_request_checks_without_changing_results(
    dummy_request, threadlocals
):
    from snovault.schema_utils import StoredDataSchemaValidator, validate
    checks = []

    def has_permission(permission, context=None):
        checks.append(permission)
        return allowed['value']

    allowed = {'value': True}
    dummy_request.has_permission = has_permission
    dummy_request.context = object()
    schema = {
        'type': 'object',
        'properties': {
            'a': {'type': 'string', 'permission': 'import_items'},
            'b': {'type': 'integer', 'requestMethod': ['POST']},
            'c': {'type': 'integer'},
        },
    }
    data = {'a': 'x', 'b': 1, 'c': 'not an integer'}
    for permitted in (True, False):
        allowed['value'] = permitted
        checks.clear()
        default_result = validate(schema, data, data)
        assert checks == ['import_items']
        checks.clear()
        stored_result = validate(schema, data, data, validator_class=StoredDataSchemaValidator)
        assert checks == []
        assert [e.message for e in stored_result[1]] == [e.message for e in default_result[1]]
        assert stored_result[0] == default_result[0]
        assert len(stored_result[1]) == 1


@pytest.fixture
def submitter_testapp(app):
    from webtest import TestApp
    return TestApp(app, {'HTTP_ACCEPT': 'application/json', 'REMOTE_USER': 'TEST_SUBMITTER'})


@pytest.mark.parametrize('batch_embed', ['true', 'false'])
def test_submitter_cannot_write_admin_only_properties_in_either_mode(submitter_testapp, testapp, batch_embed):
    collection = '/testing-post-put-patch/'
    mode = f'?batch_embed={batch_embed}'

    for admin_only in (
        {'protected': 'changed'},
        {'accession': 'SNOFL727WCB'},
        {'uuid': '0f13ff76-c559-4e70-9497-a6130841df9f'},
    ):
        res = submitter_testapp.post_json(collection + mode, {'required': 'x', **admin_only}, status=422)
        assert any("permission 'admin_only' required" in e['description'] for e in res.json['errors'])

    created = submitter_testapp.post_json(collection + mode, {'required': 'x'}, status=201).json['@graph'][0]
    assert created['protected'] == 'protected default'

    url = created['@id'] + mode
    res = submitter_testapp.patch_json(url, {'protected': 'changed'}, status=422)
    assert any("permission 'admin_only' required" in e['description'] for e in res.json['errors'])
    submitter_testapp.put_json(url, {'required': 'x', 'protected': 'changed'}, status=422)
    submitter_testapp.put_json(url, {'required': 'x', 'protected': 'protected default'}, status=200)
    assert testapp.get(created['@id']).json['protected'] == 'protected default'


def index_document(indexer_testapp, item_url, batch_embed):
    url = f'{item_url}@@index-data?datastore=database&batch_embed={str(batch_embed).lower()}'
    document = indexer_testapp.get(url).json
    document.pop('xmin')
    return document


@pytest.mark.parametrize('prefix', ['testing-link', 'testing-custom-embed'])
def test_index_document_identical_with_and_without_batch_embed(indexer_testapp, many_targets_and_sources, prefix):
    urls = [f'/{prefix}-targets/{uuid}/' for uuid in many_targets_and_sources[f'{prefix}-targets'].values()]
    urls += [f'/{prefix}-sources/{uuid}/' for uuid in many_targets_and_sources[f'{prefix}-sources']]
    for url in urls:
        batched = index_document(indexer_testapp, url, True)
        unbatched = index_document(indexer_testapp, url, False)
        # ES invalidation is driven by these two lists, so they must match exactly.
        assert batched['embedded_uuids'] == unbatched['embedded_uuids']
        assert batched['linked_uuids'] == unbatched['linked_uuids']
        assert normalize(batched) == normalize(unbatched)
