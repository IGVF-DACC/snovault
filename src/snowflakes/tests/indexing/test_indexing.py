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
        'access_key_fff7247f',
        'award_1ab88e7d',
        'image_7b272d6d',
        'lab_296e03df',
        'page_ee366aa5',
        'snowball_ba7d2ba7',
        'snowflake_a887ccf0',
        'snowfort_78fe25eb',
        'testing_bad_accession_1d729083',
        'testing_custom_embed_source_7ac06bac',
        'testing_custom_embed_target_ae393817',
        'testing_dependencies_2da45dc8',
        'testing_download_590050b4',
        'testing_link_source_7ac06bac',
        'testing_link_target_80d1f16e',
        'testing_post_put_patch_17e8079a',
        'testing_search_schema_56301551',
        'testing_search_schema_special_facets_07a1ee06',
        'testing_server_default_2479be60',
        'user_de8eb911'
    ]))
    assert actual == expected, actual
    actual = list(os.indices.get_alias('award').keys())
    expected = [
        'award_1ab88e7d',
    ]
    assert actual == expected, actual
    actual = list(sorted(os.indices.get_alias('snovault-resources').keys()))
    expected = list(sorted([
        'access_key_fff7247f',
        'award_1ab88e7d',
        'image_7b272d6d',
        'lab_296e03df',
        'page_ee366aa5',
        'snowball_ba7d2ba7',
        'snowflake_a887ccf0',
        'snowfort_78fe25eb',
        'testing_bad_accession_1d729083',
        'testing_custom_embed_source_7ac06bac',
        'testing_custom_embed_target_ae393817',
        'testing_dependencies_2da45dc8',
        'testing_download_590050b4',
        'testing_link_source_7ac06bac',
        'testing_link_target_80d1f16e',
        'testing_post_put_patch_17e8079a',
        'testing_search_schema_56301551',
        'testing_search_schema_special_facets_07a1ee06',
        'testing_server_default_2479be60',
        'user_de8eb911'
    ]))
    assert actual == expected, actual
