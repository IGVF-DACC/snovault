import pytest

pytestmark = [pytest.mark.indexing]


def test_indexing_simple_snowflakes(testapp, workbook):
    import time
    response = testapp.post_json('/testing-post-put-patch/', {'required': ''})
    uuid1 = response.json['@graph'][0]['uuid']
    response = testapp.post_json('/testing-post-put-patch/', {'required': ''})
    uuid2 = response.json['@graph'][0]['uuid']
    print('Waiting for results in search')
    time.sleep(30)
    response = testapp.get('/search/?type=TestingPostPutPatch')
    assert len(response.json['@graph']) == 2
