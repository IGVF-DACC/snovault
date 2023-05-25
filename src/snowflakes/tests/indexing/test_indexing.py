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
        'access_key_007c5768',
        'award_577215e5',
        'image_7276b881',
        'lab_9a0f637c',
        'page_736e4e01',
        'snowball_33689767',
        'snowflake_1ce7d631',
        'snowfort_1bdad6c4',
        'testing_bad_accession_cacbadd6',
        'testing_custom_embed_source_95665017',
        'testing_custom_embed_target_2639e036',
        'testing_dependencies_8510f6fe',
        'testing_download_f69a0800',
        'testing_link_source_f136c551',
        'testing_link_target_d22138ac',
        'testing_post_put_patch_e4d8c17d',
        'testing_search_schema_addb6e99',
        'testing_search_schema_special_facets_3c488a1f',
        'testing_server_default_ddacd7c1',
        'user_ee1e123c'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_577215e5',
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_007c5768',
        'award_577215e5',
        'image_7276b881',
        'lab_9a0f637c',
        'page_736e4e01',
        'snowball_33689767',
        'snowflake_1ce7d631',
        'snowfort_1bdad6c4',
        'testing_bad_accession_cacbadd6',
        'testing_custom_embed_source_95665017',
        'testing_custom_embed_target_2639e036',
        'testing_dependencies_8510f6fe',
        'testing_download_f69a0800',
        'testing_link_source_f136c551',
        'testing_link_target_d22138ac',
        'testing_post_put_patch_e4d8c17d',
        'testing_search_schema_addb6e99',
        'testing_search_schema_special_facets_3c488a1f',
        'testing_server_default_ddacd7c1',
        'user_ee1e123c'
    ]))
    assert actual == expected, actual
