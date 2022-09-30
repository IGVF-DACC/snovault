import pytest

from .features.conftest import app_settings, app, workbook

pytestmark = [pytest.mark.indexing]


def test_indexing_simple_snowflakes(testapp):
    import time
    response = testapp.post_json('/testing-post-put-patch/', {'required': ''})
    uuid1 = response.json['@graph'][0]['uuid']
    response = testapp.post_json('/testing-post-put-patch/', {'required': ''})
    uuid2 = response.json['@graph'][0]['uuid']
    time.sleep(30)
    response = testapp.get('/search/?type=TestingPostPutPatch')
    assert len(response.json['@graph']) == 2
