import pytest


def _type_length():
    # Not a fixture as we need to parameterize tests on this
    from ..loadxl import ORDER
    from pkg_resources import resource_stream
    import codecs
    import json
    utf8 = codecs.getreader('utf-8')
    return {
        name: len(json.load(utf8(resource_stream('snowflakes', 'tests/data/inserts/%s.json' % name))))
        for name in ORDER
        if name != 'access_key'
    }


TYPE_LENGTH = _type_length()

PUBLIC_COLLECTIONS = [
    'lab',
    'award',
]


def test_home(anonhtmltestapp):
    res = anonhtmltestapp.get('/', status=200)


def test_home_json(testapp):
    res = testapp.get('/', status=200)
    assert res.json['@type']


def test_home_app_version(testapp):
    res = testapp.get('/', status=200)
    assert 'app_version' in res.json


def test_vary_html(anonhtmltestapp):
    res = anonhtmltestapp.get('/', status=200)
    assert res.vary is not None
    assert 'Accept' in res.vary


def test_vary_json(anontestapp):
    res = anontestapp.get('/', status=200)
    assert res.vary is not None
    assert 'Accept' in res.vary


@pytest.mark.parametrize('item_type', [k for k in TYPE_LENGTH if k != 'user'])
def test_collections_anon(workbook, anontestapp, item_type):
    res = anontestapp.get('/' + item_type).follow(status=200)
    assert '@graph' in res.json


@pytest.mark.parametrize('item_type', [k for k in TYPE_LENGTH if k != 'user'])
def test_html_collections_anon(workbook, anonhtmltestapp, item_type):
    res = anonhtmltestapp.get('/' + item_type).follow(status=200)


@pytest.mark.parametrize('item_type', TYPE_LENGTH)
def test_html_collections(workbook, htmltestapp, item_type):
    res = htmltestapp.get('/' + item_type).follow(status=200)


@pytest.mark.slow
@pytest.mark.parametrize('item_type', TYPE_LENGTH)
def test_html_pages(workbook, testapp, htmltestapp, item_type):
    res = testapp.get('/%s?limit=all' % item_type).follow(status=200)
    for item in res.json['@graph']:
        res = htmltestapp.get(item['@id'])


@pytest.mark.slow
@pytest.mark.parametrize('item_type', [k for k in TYPE_LENGTH if k != 'user'])
def test_html_server_pages(workbook, item_type, wsgi_server):
    from webtest import TestApp
    testapp = TestApp(wsgi_server)
    res = testapp.get(
        '/%s?limit=all' % item_type,
        headers={'Accept': 'application/json'},
    ).follow(
        status=200,
        headers={'Accept': 'application/json'},
    )
    for item in res.json['@graph']:
        res = testapp.get(item['@id'], status=200)
        assert b'Internal Server Error' not in res.body


@pytest.mark.parametrize('item_type', TYPE_LENGTH)
def test_json(testapp, item_type):
    res = testapp.get('/' + item_type).follow(status=200)
    assert res.json['@type']


def test_json_basic_auth(anonhtmltestapp):
    from base64 import b64encode
    from snovault.compat import ascii_native_
    url = '/'
    value = 'Authorization: Basic %s' % ascii_native_(b64encode(b'nobody:pass'))
    res = anonhtmltestapp.get(url, headers={'Authorization': value}, status=401)
    assert res.content_type == 'application/json'


def test_load_sample_data(
        award,
        lab,
        submitter,
        snowball,
        snowflake,
):
    assert True, 'Fixtures have loaded sample data'


def test_abstract_collection(testapp, snowball):
    testapp.get('/Snowset/{accession}'.format(**snowball))
    testapp.get('/snowsets/{accession}'.format(**snowball))


def test_views_object_with_select_calculated_properties(workbook, testapp):
    r = testapp.get('/snowballs/')
    at_id = r.json['@graph'][0]['@id']
    r = testapp.get(at_id + '?frame=object')
    assert 'test_calculated' in r.json
    assert 'another_test_calculated' in r.json
    assert 'conditional_test_calculated' in r.json
    r = testapp.get(at_id + '?frame=object&skip_calculated=true')
    assert 'test_calculated' not in r.json
    assert 'another_test_calculated' not in r.json
    assert 'conditional_test_calculated' not in r.json
    r = testapp.get(at_id + '?frame=object_with_select_calculated_properties')
    assert 'test_calculated' not in r.json
    assert 'another_test_calculated' not in r.json
    assert 'conditional_test_calculated' not in r.json
    r = testapp.get(at_id + '?frame=object_with_select_calculated_properties&field=test_calculated')
    assert 'test_calculated' in r.json
    assert 'another_test_calculated' not in r.json
    assert 'conditional_test_calculated' not in r.json
    r = testapp.get(
        at_id + '?frame=object_with_select_calculated_properties&field=test_calculated&field=another_test_calculated'
    )
    assert 'test_calculated' in r.json
    assert 'another_test_calculated' in r.json
    assert 'conditional_test_calculated' not in r.json
    r = testapp.get(
        at_id + '?frame=object_with_select_calculated_properties&field=test_calculated&field=conditional_test_calculated'
    )
    assert 'test_calculated' in r.json
    assert 'another_test_calculated' not in r.json
    assert 'conditional_test_calculated' in r.json


def test_view_history_view(workbook, testapp):
    r = testapp.get('/snowballs/SNOSS000AEN/?frame=history')
    assert 'latest' in r.json
    assert r.json['rid'] == '/snowballs/SNOSS000AEN/'
    assert 'history' in r.json
    assert len(r.json['history']) == 1


def test_views_history_view_resolves_access_key_to_user(snowball, testapp, access_key, anontestapp):
    from .test_access_key import auth_header
    # Given a snowball posted by system with one version and empty description:
    r = testapp.get(f'{snowball["@id"]}?frame=history')
    assert len(r.json['history']) == 1
    assert r.json['latest']['props']['description'] == ''
    assert r.json['latest']['userid'] == 'remoteuser.TEST'
    assert 'user_from_access_key' not in r.json['latest']
    # When it's patched by a user using an auth key:
    headers = {'Authorization': auth_header(access_key)}
    r = anontestapp.patch_json(
        snowball['@id'],
        {
            'description': 'another example snowball'
        },
        headers=headers,
    )
    # Then there are two versions of history and it shows user title from access key:
    r = testapp.get(f'{snowball["@id"]}?frame=history')
    assert len(r.json['history']) == 2
    assert r.json['latest']['props']['description'] == 'another example snowball'
    assert 'accesskey' in r.json['latest']['userid']
    assert 'user_from_access_key' in r.json['latest']
    assert r.json['latest']['user_from_access_key'] == 'ENCODE Submitter'
    # And history shows most recent edit first:
    assert r.json['history'][0] == r.json['latest']
    # And only shows user from access key if it was modified with an access key:
    assert 'user_from_access_key' in r.json['history'][0]
    assert 'user_from_access_key' not in r.json['history'][1]


@pytest.mark.slow
@pytest.mark.parametrize(('item_type', 'length'), TYPE_LENGTH.items())
def test_load_workbook(workbook, testapp, item_type, length):
    # testdata must come before testapp in the funcargs list for their
    # savepoints to be correctly ordered.
    res = testapp.get('/%s/?limit=all' % item_type).maybe_follow(status=200)
    assert len(res.json['@graph']) == length


@pytest.mark.slow
def test_collection_limit(workbook, testapp):
    res = testapp.get('/awards/?limit=2', status=200)
    assert len(res.json['@graph']) == 2


def test_collection_post(testapp):
    item = {
        'name': 'NIS39393',
        'title': 'Grant to make snow',
        'project': 'ENCODE',
        'rfa': 'ENCODE3',
    }
    testapp.post_json('/award', item, status=201)


def test_collection_post_bad_json(testapp):
    item = {'foo': 'bar'}
    res = testapp.post_json('/award', item, status=422)
    assert res.json['errors']


def test_collection_post_malformed_json(testapp):
    item = '{'
    headers = {'Content-Type': 'application/json'}
    res = testapp.post('/award', item, status=400, headers=headers)
    assert res.json['detail'].startswith('Expecting')


def test_collection_post_missing_content_type(testapp):
    item = '{}'
    testapp.post('/award', item, status=415)


def test_collection_post_bad_(anontestapp):
    from base64 import b64encode
    from snovault.compat import ascii_native_
    value = 'Authorization: Basic %s' % ascii_native_(b64encode(b'nobody:pass'))
    anontestapp.post_json('/award', {}, headers={'Authorization': value}, status=401)


def test_collection_actions_filtered_by_permission(workbook, testapp, anontestapp):
    res = testapp.get('/pages/')
    assert any(action for action in res.json.get('actions', []) if action['name'] == 'add')

    res = anontestapp.get('/pages/')
    assert not any(action for action in res.json.get('actions', []) if action['name'] == 'add')


def test_item_actions_filtered_by_permission(testapp, authenticated_testapp, award):
    location = award['@id']

    res = testapp.get(location)
    assert any(action for action in res.json.get('actions', []) if action['name'] == 'edit')

    res = authenticated_testapp.get(location)
    assert not any(action for action in res.json.get('actions', []) if action['name'] == 'edit')


def test_collection_put(testapp, execute_counter):
    initial = {
        'name': 'NIS39393',
        'title': 'Grant to make snow',
        'project': 'ENCODE',
        'rfa': 'ENCODE3',
    }
    item_url = testapp.post_json('/award', initial).location

    with execute_counter.expect(1):
        item = testapp.get(item_url).json

    for key in initial:
        assert item[key] == initial[key]

    update = {
        'name': 'NIS440404',
        'title': 'Frozen wastland',
        'project': 'ENCODE',
        'rfa': 'ENCODE3',
    }
    testapp.put_json(item_url, update, status=200)

    res = testapp.get('/' + item['uuid']).follow().json

    for key in update:
        assert res[key] == update[key]


def test_post_duplicate_uuid(testapp, award):
    item = {
        'uuid': award['uuid'],
        'name': 'NIS39393',
        'title': 'Grant to make snow',
        'project': 'ENCODE',
        'rfa': 'ENCODE3',
    }
    testapp.post_json('/award', item, status=409)


def test_user_effective_principals(submitter, lab, anontestapp, execute_counter):
    email = submitter['email']
    with execute_counter.expect(1):
        res = anontestapp.get('/@@testing-user',
                              extra_environ={'REMOTE_USER': str(email)})
    assert sorted(res.json['effective_principals']) == [
        'group.submitter',
        'lab.%s' % lab['uuid'],
        'remoteuser.%s' % email,
        'submits_for.%s' % lab['uuid'],
        'system.Authenticated',
        'system.Everyone',
        'userid.%s' % submitter['uuid'],
        'viewing_group.ENCODE',
    ]


def test_page_toplevel(workbook, anontestapp):
    res = anontestapp.get('/test-section/', status=200)
    assert res.json['@id'] == '/test-section/'

    res = anontestapp.get('/pages/test-section/', status=301)
    assert res.location == 'http://localhost/test-section/'


def test_page_nested(workbook, anontestapp):
    res = anontestapp.get('/test-section/subpage/', status=200)
    assert res.json['@id'] == '/test-section/subpage/'


def test_page_nested_in_progress(workbook, anontestapp):
    anontestapp.get('/test-section/subpage-in-progress/', status=403)


def test_page_homepage(workbook, anontestapp):
    res = anontestapp.get('/pages/homepage/', status=200)
    assert res.json['canonical_uri'] == '/'

    res = anontestapp.get('/', status=200)
    assert 'default_page' in res.json
    assert res.json['default_page']['@id'] == '/pages/homepage/'


def test_page_collection_default(workbook, anontestapp):
    res = anontestapp.get('/pages/images/', status=200)
    assert res.json['canonical_uri'] == '/images/'

    res = anontestapp.get('/images/', status=200)
    assert 'default_page' in res.json
    assert res.json['default_page']['@id'] == '/pages/images/'


def test_jsonld_context(testapp):
    res = testapp.get('/terms/')
    assert res.json


def test_jsonld_term(testapp):
    res = testapp.get('/terms/submitted_by')
    assert res.json


@pytest.mark.slow
@pytest.mark.parametrize('item_type', TYPE_LENGTH)
def test_index_data_workbook(workbook, testapp, indexer_testapp, item_type):
    res = testapp.get('/%s?limit=all' % item_type).follow(status=200)
    for item in res.json['@graph']:
        indexer_testapp.get(item['@id'] + '@@index-data')


@pytest.mark.parametrize('item_type', TYPE_LENGTH)
def test_profiles(testapp, item_type):
    from jsonschema import Draft202012Validator
    res = testapp.get('/profiles/%s.json' % item_type).maybe_follow(status=200)
    errors = Draft202012Validator.check_schema(res.json)
    assert not errors


def test_bad_frame(testapp, award):
    res = testapp.get(award['@id'] + '?frame=bad', status=404)
    assert res.json['detail'] == '?frame=bad'
