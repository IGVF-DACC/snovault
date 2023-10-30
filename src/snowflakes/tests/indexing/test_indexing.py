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
        'access_key_5bd72e25',
        'award_8ab12598',
        'image_9d79d5e4',
        'lab_dd2e527f',
        'page_54c9ebeb',
        'snowball_6f4c73a4',
        'snowflake_30db45cf',
        'snowfort_5e0163f6',
        'testing_bad_accession_68bd87b2',
        'testing_custom_embed_source_d90ac323',
        'testing_custom_embed_target_6881adca',
        'testing_dependencies_965e4e95',
        'testing_download_ff92c2cb',
        'testing_link_source_de2a5001',
        'testing_link_target_1b833428',
        'testing_post_put_patch_a469c52f',
        'testing_search_schema_cac5d36a',
        'testing_search_schema_special_facets_ce73ae5f',
        'testing_server_default_fe00209c',
        'user_5466c376'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_8ab12598'
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_5bd72e25',
        'award_8ab12598',
        'image_9d79d5e4',
        'lab_dd2e527f',
        'page_54c9ebeb',
        'snowball_6f4c73a4',
        'snowflake_30db45cf',
        'snowfort_5e0163f6',
        'testing_bad_accession_68bd87b2',
        'testing_custom_embed_source_d90ac323',
        'testing_custom_embed_target_6881adca',
        'testing_dependencies_965e4e95',
        'testing_download_ff92c2cb',
        'testing_link_source_de2a5001',
        'testing_link_target_1b833428',
        'testing_post_put_patch_a469c52f',
        'testing_search_schema_cac5d36a',
        'testing_search_schema_special_facets_ce73ae5f',
        'testing_server_default_fe00209c',
        'user_5466c376'
    ]))
    assert actual == expected, actual
