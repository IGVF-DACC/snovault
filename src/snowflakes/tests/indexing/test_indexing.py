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
        'image_2fa710c5',
        'lab_ca4719b2',
        'page_06b7b3c1',
        'snowball_fb0e82a6',
        'snowflake_cf91c1ba',
        'snowfort_be941cb2',
        'testing_bad_accession_597d18c9',
        'testing_custom_embed_source_0cbcd5e3',
        'testing_custom_embed_target_62547261',
        'testing_dependencies_92c80b0d',
        'testing_download_356eca88',
        'testing_link_source_7cb36f2a',
        'testing_link_target_65ce962c',
        'testing_post_put_patch_d091fc57',
        'testing_search_schema_912808ca',
        'testing_search_schema_special_facets_7e8922e1',
        'testing_server_default_1a963606',
        'user_8de028e4'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_8ab12598'
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_b135add2',
        'award_d7f390e2',
        'image_2fa710c5',
        'lab_ca4719b2',
        'page_06b7b3c1',
        'snowball_fb0e82a6',
        'snowflake_cf91c1ba',
        'snowfort_be941cb2',
        'testing_bad_accession_597d18c9',
        'testing_custom_embed_source_0cbcd5e3',
        'testing_custom_embed_target_62547261',
        'testing_dependencies_92c80b0d',
        'testing_download_356eca88',
        'testing_link_source_7cb36f2a',
        'testing_link_target_65ce962c',
        'testing_post_put_patch_d091fc57',
        'testing_search_schema_912808ca',
        'testing_search_schema_special_facets_7e8922e1',
        'testing_server_default_1a963606',
        'user_8de028e4'
    ]))
    assert actual == expected, actual
