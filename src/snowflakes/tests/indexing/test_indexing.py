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
        'access_key_db9ff764',
        'award_c714d005',
        'image_dc6d8410',
        'lab_e1f98812',
        'page_5ff009f3',
        'snowball_9839b724',
        'snowflake_7d4e7537',
        'snowfort_bfdace71',
        'testing_bad_accession_e614d91a',
        'testing_custom_embed_source_b3cdad26',
        'testing_custom_embed_target_5ae1230c',
        'testing_dependencies_79304498',
        'testing_download_fcbce128',
        'testing_link_source_95b68062',
        'testing_link_target_52146934',
        'testing_post_put_patch_86f46073',
        'testing_search_schema_f681757b',
        'testing_search_schema_special_facets_0c4a35e6',
        'testing_server_default_5f4a711b',
        'user_54004781'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_c714d005',
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_db9ff764',
        'award_c714d005',
        'image_dc6d8410',
        'lab_e1f98812',
        'page_5ff009f3',
        'snowball_9839b724',
        'snowflake_7d4e7537',
        'snowfort_bfdace71',
        'testing_bad_accession_e614d91a',
        'testing_custom_embed_source_b3cdad26',
        'testing_custom_embed_target_5ae1230c',
        'testing_dependencies_79304498',
        'testing_download_fcbce128',
        'testing_link_source_95b68062',
        'testing_link_target_52146934',
        'testing_post_put_patch_86f46073',
        'testing_search_schema_f681757b',
        'testing_search_schema_special_facets_0c4a35e6',
        'testing_server_default_5f4a711b',
        'user_54004781'
    ]))
    assert actual == expected, actual
