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
        'access_key_828db54a',
        'award_0928c743',
        'image_71f1370f',
        'lab_97f7fb39',
        'page_9e9f92d5',
        'snowball_c99d8a41',
        'snowflake_8d771cc3',
        'snowfort_2eaa2355',
        'testing_bad_accession_f37ff11d',
        'testing_custom_embed_source_562e6c63',
        'testing_custom_embed_target_ebd058c8',
        'testing_dependencies_d4c0e10a',
        'testing_download_9e40e0b4',
        'testing_link_source_5a382472',
        'testing_link_target_ed04b07b',
        'testing_post_put_patch_9f695bfd',
        'testing_search_schema_8e208318',
        'testing_search_schema_special_facets_98447bdb',
        'testing_server_default_9b7e7a5c',
        'user_7a155f0f'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_0928c743',
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_828db54a',
        'award_0928c743',
        'image_71f1370f',
        'lab_97f7fb39',
        'page_9e9f92d5',
        'snowball_c99d8a41',
        'snowflake_8d771cc3',
        'snowfort_2eaa2355',
        'testing_bad_accession_f37ff11d',
        'testing_custom_embed_source_562e6c63',
        'testing_custom_embed_target_ebd058c8',
        'testing_dependencies_d4c0e10a',
        'testing_download_9e40e0b4',
        'testing_link_source_5a382472',
        'testing_link_target_ed04b07b',
        'testing_post_put_patch_9f695bfd',
        'testing_search_schema_8e208318',
        'testing_search_schema_special_facets_98447bdb',
        'testing_server_default_9b7e7a5c',
        'user_7a155f0f'
    ]))
    assert actual == expected, actual
