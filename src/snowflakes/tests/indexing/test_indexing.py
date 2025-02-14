import pytest

pytestmark = [pytest.mark.indexing]


def test_indexing_simple_snowflakes(testapp, workbook, poll_until_indexing_is_done):
    import time
    response = testapp.post_json('/testing-post-put-patch/', {'required': ''})
    uuid1 = response.json['@graph'][0]['uuid']
    response = testapp.post_json('/testing-post-put-patch/', {'required': ''})
    uuid2 = response.json['@graph'][0]['uuid']
    print('Waiting for results in search')
    poll_until_indexing_is_done(testapp)
    response = testapp.get('/search/?type=TestingPostPutPatch')
    assert len(response.json['@graph']) == 2


def test_indexing_updated_name_invalidates_dependents(testapp, dummy_request, workbook, poll_until_indexing_is_done):
    response = testapp.get('/search/?type=User&lab.name=j-michael-cherry')
    assert len(response.json['@graph']) == 17
    testapp.patch_json(
        '/labs/j-michael-cherry/',
        {'name': 'some-other-name'}
    )
    poll_until_indexing_is_done(testapp)
    response = testapp.get('/search/?type=User&lab.name=some-other-name')
    assert len(response.json['@graph']) == 17
    testapp.get('/search/?type=User&lab.name=j-michael-cherry', status=404)
    testapp.patch_json(
        '/labs/some-other-name/',
        {'name': 'j-michael-cherry'}
    )
    poll_until_indexing_is_done(testapp)
    testapp.get('/search/?type=User&lab.name=some-other-lab', status=404)
    response = testapp.get('/search/?type=User&lab.name=j-michael-cherry')
    assert len(response.json['@graph']) == 17


def test_indexing_opensearch_mappings_exist(testapp, registry, dummy_request, workbook, poll_until_indexing_is_done):
    from snovault.elasticsearch.interfaces import ELASTIC_SEARCH
    os = registry[ELASTIC_SEARCH]
    actual = list(sorted(os.indices.get('*').keys()))
    expected = list(sorted([
        'access_key_b135add2',
        'award_d7f390e2',
        'image_0611cffc',
        'lab_ca4719b2',
        'page_f311e755',
        'snowball_fb0e82a6',
        'snowflake_cf91c1ba',
        'snowfort_be941cb2',
        'testing_bad_accession_10bbcf16',
        'testing_custom_embed_source_551f8ce8',
        'testing_custom_embed_target_867d5dd9',
        'testing_dependencies_92c80b0d',
        'testing_download_356eca88',
        'testing_link_source_1d2673dd',
        'testing_link_target_b28678af',
        'testing_post_put_patch_4e15f857',
        'testing_search_schema_912808ca',
        'testing_search_schema_special_facets_82782cf3',
        'testing_server_default_d476d516',
        'user_8de028e4'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_d7f390e2'
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_b135add2',
        'award_d7f390e2',
        'image_0611cffc',
        'lab_ca4719b2',
        'page_f311e755',
        'snowball_fb0e82a6',
        'snowflake_cf91c1ba',
        'snowfort_be941cb2',
        'testing_bad_accession_10bbcf16',
        'testing_custom_embed_source_551f8ce8',
        'testing_custom_embed_target_867d5dd9',
        'testing_dependencies_92c80b0d',
        'testing_download_356eca88',
        'testing_link_source_1d2673dd',
        'testing_link_target_b28678af',
        'testing_post_put_patch_4e15f857',
        'testing_search_schema_912808ca',
        'testing_search_schema_special_facets_82782cf3',
        'testing_server_default_d476d516',
        'user_8de028e4'
    ]))
    assert actual == expected, actual
