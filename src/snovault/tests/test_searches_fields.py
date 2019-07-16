import pytest


def test_searches_fields_response_field_init():
    from snovault.elasticsearch.searches.fields import ResponseField
    rf = ResponseField()
    assert isinstance(rf, ResponseField)


def test_searches_fields_basic_search_response_field_init():
    from snovault.elasticsearch.searches.fields import BasicSearchWithFacetsResponseField
    brf = BasicSearchWithFacetsResponseField()
    assert isinstance(brf, BasicSearchWithFacetsResponseField)


def test_searches_fields_basic_search_response_build_query():
    from snovault.elasticsearch.searches.fields import BasicSearchWithFacetsResponseField
    brf = BasicSearchWithFacetsResponseField()
    assert False


def test_searches_fields_basic_search_response_execute_query():
    from snovault.elasticsearch.searches.fields import BasicSearchWithFacetsResponseField
    brf = BasicSearchWithFacetsResponseField()
    assert False


def test_searches_fields_basic_search_response_format_results_query():
    from snovault.elasticsearch.searches.fields import BasicSearchWithFacetsResponseField
    brf = BasicSearchWithFacetsResponseField()
    assert False


def test_searches_fields_title_field_init():
    from snovault.elasticsearch.searches.fields import TitleField
    tf = TitleField()
    assert isinstance(tf, TitleField)


def test_searches_fields_title_field_title_value():
    from snovault.elasticsearch.searches.fields import TitleField
    tf = TitleField(title='Search')
    rtf = tf.render()
    assert rtf == {'title': 'Search'}
