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
    print(actual)
    expected = list(sorted([
        'access_key_82be1c13',
        'award_0be0c601',
        'image_8e6ce64b',
        'lab_108fa712',
        'page_26b8dd9c',
        'snowball_f1f073f6',
        'snowflake_c9d175a6',
        'snowfort_ed04b837',
        'testing_bad_accession_7f7f97b5',
        'testing_custom_embed_source_9a7958f8',
        'testing_custom_embed_target_dfbad0af',
        'testing_dependencies_b31072f0',
        'testing_download_597dc870',
        'testing_link_source_d8e116cf',
        'testing_link_target_ff03d99d',
        'testing_post_put_patch_8c62839a',
        'testing_search_schema_09fe333e',
        'testing_search_schema_special_facets_7a3f7300',
        'testing_server_default_b0b617ab',
        'user_a15abba1'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_1ab88e7d',
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_82be1c13',
        'award_0be0c601',
        'image_8e6ce64b',
        'lab_108fa712',
        'page_26b8dd9c',
        'snowball_f1f073f6',
        'snowflake_c9d175a6',
        'snowfort_ed04b837',
        'testing_bad_accession_7f7f97b5',
        'testing_custom_embed_source_9a7958f8',
        'testing_custom_embed_target_dfbad0af',
        'testing_dependencies_b31072f0',
        'testing_download_597dc870',
        'testing_link_source_d8e116cf',
        'testing_link_target_ff03d99d',
        'testing_post_put_patch_8c62839a',
        'testing_search_schema_09fe333e',
        'testing_search_schema_special_facets_7a3f7300',
        'testing_server_default_b0b617ab',
        'user_a15abba1'
    ]))
    assert actual == expected, actual
