import pytest
from uuid import uuid4

N_SOURCES = 7
CACHE_NAMES = (
    'snovault.connection.embed_cache',
    'snovault.connection.item_cache',
    'snovault.connection.key_cache',
)


@pytest.fixture(autouse=True)
def autouse_external_tx(external_tx):
    pass


@pytest.fixture
def many_targets_and_sources(testapp):
    uuids = {}
    for prefix in ('testing-link', 'testing-custom-embed'):
        for name in ('one', 'two'):
            testapp.post_json(f'/{prefix}-targets/', {'name': name}, status=201)
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
    assert batched == unbatched
    if 'frame=embedded' in url:
        assert all(isinstance(member, dict) for member in batched['reverse'])


def test_source_rendering_identical_with_and_without_batch_embed(testapp, many_targets_and_sources):
    for uuid in many_targets_and_sources['testing-link-sources']:
        url = f'/testing-link-sources/{uuid}/?frame=object'
        assert get_json(testapp, url, True) == get_json(testapp, url, False)


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
    assert results[True] == results[False]
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
    assert results[True] == results[False]
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
