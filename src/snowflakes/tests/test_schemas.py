import pytest
from pkg_resources import resource_listdir

SCHEMA_FILES = [
    f for f in resource_listdir('snowflakes', 'schemas')
    if f.endswith('.json')
]


@pytest.mark.parametrize('schema', SCHEMA_FILES)
def test_load_schema(schema):
    from snovault.schema_utils import load_schema
    assert load_schema('snowflakes:schemas/%s' % schema)


def test_linkTo_saves_uuid(root, submitter, lab):
    item = root['users'][submitter['uuid']]
    assert item.properties['submits_for'] == [lab['uuid']]


def test_mixinProperties():
    from snovault.schema_utils import load_schema
    schema = load_schema('snowflakes:schemas/access_key.json')
    assert schema['properties']['uuid']['type'] == 'string'


def test_dependencies(testapp):
    collection_url = '/testing-dependencies/'
    testapp.post_json(collection_url, {'dep1': 'dep1', 'dep2': 'dep2'}, status=201)
    testapp.post_json(collection_url, {'dep1': 'dep1'}, status=422)
    testapp.post_json(collection_url, {'dep2': 'dep2'}, status=422)
    testapp.post_json(collection_url, {'dep1': 'dep1', 'dep2': 'disallowed'}, status=422)


def test_page_schema_validates_parent_is_not_collection_default_page(testapp):
    res = testapp.post_json('/pages/', {'name': 'users', 'title': 'Users'})
    uuid = res.json['@graph'][0]['@id']
    testapp.post_json('/pages/', {'parent': uuid, 'name': 'test', 'title': 'Test'}, status=422)


def test_changelogs(testapp, registry):
    from snovault import TYPES
    for typeinfo in registry[TYPES].by_item_type.values():
        changelog = typeinfo.schema.get('changelog')
        if changelog is not None:
            res = testapp.get(changelog)
            assert res.status_int == 200, changelog
            assert res.content_type == 'text/markdown'


def test_schemas_etag(testapp):
    etag = testapp.get('/profiles/', status=200).etag
    assert etag
    testapp.get('/profiles/', headers={'If-None-Match': etag}, status=304)


def test_schemas_type_hierarchy_view(testapp):
    result = testapp.get('/profiles/')
    assert '_hierarchy' in result.json
    actual = result.json['_hierarchy']
    expected = {
        'Item': {
            'Award': {},
            'Lab': {},
            'AccessKey': {},
            'Image': {},
            'Page': {},
            'Snowset': {
                'Snowball': {},
                'Snowfort': {}
            },
            'Snowflake': {},
            'User': {},
            'TestingBadAccession': {},
            'TestingCustomEmbedSource': {},
            'TestingCustomEmbedTarget': {},
            'TestingDependencies': {},
            'TestingDownload': {},
            'TestingLinkSource': {},
            'TestingLinkTarget': {},
            'TestingPostPutPatch': {},
            'TestingSearchSchema': {},
            'TestingSearchSchemaSpecialFacets': {},
            'TestingServerDefault': {}
        }
    }
    assert actual == expected


def test_schemas_collection_titles_view(testapp):
    actual = testapp.get('/collection-titles/').json
    expected = {
        'awards': 'Awards (Grants)',
        'Award': 'Awards (Grants)',
        'award': 'Awards (Grants)',
        'labs': 'Labs',
        'Lab': 'Labs',
        'lab': 'Labs',
        'access-keys': 'Access keys',
        'AccessKey': 'Access keys',
        'access_key': 'Access keys',
        'images': 'Image',
        'Image': 'Image',
        'image': 'Image',
        'pages': 'Pages',
        'Page': 'Pages',
        'page': 'Pages',
        'snowballs': 'Snowball style snowset',
        'Snowball': 'Snowball style snowset',
        'snowball': 'Snowball style snowset',
        'snowflakes': 'Snowflakes',
        'Snowflake': 'Snowflakes',
        'snowflake': 'Snowflakes',
        'snowforts': 'Snowfort style snowset',
        'Snowfort': 'Snowfort style snowset',
        'snowfort': 'Snowfort style snowset',
        'snowsets': 'Snowsets',
        'Snowset': 'Snowsets',
        'users': 'Snowflake  Users',
        'User': 'Snowflake  Users',
        'user': 'Snowflake  Users',
        'testing-downloads': 'Test download collection',
        'TestingDownload': 'Test download collection',
        'testing_download': 'Test download collection',
        '@type': ['CollectionTitles']
    }
    assert actual == expected


def test_etag_if_match_tid(testapp, award):
    res = testapp.get(award['@id'] + '?frame=edit', status=200)
    etag = res.etag
    testapp.patch_json(award['@id'], {}, headers={'If-Match': etag}, status=200)
    testapp.patch_json(award['@id'], {}, headers={'If-Match': etag}, status=412)
