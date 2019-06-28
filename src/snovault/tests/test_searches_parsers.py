import pytest


def test_searches_parsers_params_parser_init(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    p = ParamsParser(dummy_request)
    assert isinstance(p, ParamsParser)
    assert p._request is dummy_request


def test_searches_parsers_params_parser_query_string(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment'
    p = ParamsParser(dummy_request)
    assert 'type' in p._request.params
    assert p._request.params.getall('type') == ['Experiment']


def test_searches_parsers_params_parser_query_string_not(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type!=Experiment'
    p = ParamsParser(dummy_request)
    assert 'type!' in p._request.params


def test_searches_parsers_params_parser_get_filters_by_condition_none(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment&type=File&field=status'
    p = ParamsParser(dummy_request)
    assert p.get_filters_by_condition() == [
        ('type', 'Experiment'),
        ('type', 'File'),
        ('field', 'status')
    ]


def test_searches_parsers_params_parser_get_filters_by_condition_key_field(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment&type=File&field=status'
    p = ParamsParser(dummy_request)
    assert p.get_filters_by_condition(
        key_and_value_condition=lambda k, _: k == 'field'
    ) == [
        ('field', 'status')
    ]


def test_searches_parsers_params_parser_get_filters_by_condition_key_type(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment&type=File&field=status'
    p = ParamsParser(dummy_request)
    assert p.get_filters_by_condition(
        key_and_value_condition=lambda k, _: k == 'type'
    ) == [
        ('type', 'Experiment'),
        ('type', 'File')
    ]


def test_searches_parsers_params_parser_get_filters_by_condition_value_status(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment&type=File&field=status'
    p = ParamsParser(dummy_request)
    assert p.get_filters_by_condition(
        key_and_value_condition=lambda _, v: v == 'status'
    ) == [
        ('field', 'status')
    ]


def test_searches_parsers_params_parser_get_filters_by_condition_key_type_value_file(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment&type=File&field=status'
    p = ParamsParser(dummy_request)
    assert p.get_filters_by_condition(
        key_and_value_condition=lambda k, v: k == 'type' and v == 'File'
    ) == [
        ('type', 'File')
    ]


def test_searches_parsers_params_parser_get_filters_by_condition_contains_letter(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = 'type=Experiment&type=File&field=status'
    p = ParamsParser(dummy_request)
    assert p.get_filters_by_condition(
        key_and_value_condition=lambda k, v: 't' in k and 'F' in v
    ) == [
        ('type', 'File')
    ]


def test_searches_parsers_params_parser_get_key_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&status=archived&type!=Item&status!=released'
    )
    p = ParamsParser(dummy_request)
    assert p.get_key_filters(key='status') == [
        ('status', 'archived'),
        ('status!', 'released')
    ]


def test_searches_parsers_params_parser_get_type_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&field=status&type!=Item'
    )
    p = ParamsParser(dummy_request)
    assert p.get_type_filters() == [
        ('type', 'Experiment'),
        ('type', 'File'),
        ('type!', 'Item')
    ]


def test_searches_parsers_params_parser_get_search_term_filters_empty(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&field=status&type!=Item'
    )
    p = ParamsParser(dummy_request)
    assert p.get_search_term_filters() == []


def test_searches_parsers_params_parser_get_search_term_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&field=status&type!=Item'
        '&searchTerm=my+favorite+experiment&searchTerm=my+other+experiment'
        '&searchTerm!=whatever'
    )
    p = ParamsParser(dummy_request)
    assert p.get_search_term_filters() == [
        ('searchTerm', 'my favorite experiment'),
        ('searchTerm', 'my other experiment'),
        ('searchTerm!', 'whatever')
    ]


def test_searches_parsers_params_parser_get_must_match_search_term_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&field=status&type!=Item'
        '&searchTerm=my+favorite+experiment&searchTerm=my+other+experiment'
        '&searchTerm!=whatever'
    )
    p = ParamsParser(dummy_request)
    assert p.get_must_match_search_term_filters() == [
        ('searchTerm', 'my favorite experiment'),
        ('searchTerm', 'my other experiment')
    ]


def test_searches_parsers_params_parser_get_must_not_match_search_term_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&field=status&type!=Item'
        '&searchTerm=my+favorite+experiment&searchTerm=my+other+experiment'
        '&searchTerm!=whatever'
    )
    p = ParamsParser(dummy_request)
    assert p.get_must_not_match_search_term_filters() == [
        ('searchTerm!', 'whatever')
    ]


def test_searches_parsers_params_parser_get_field_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&field=status&type!=Item'
        '&searchTerm=my+favorite+experiment&searchTerm=my+other+experiment'
    )
    p = ParamsParser(dummy_request)
    assert p.get_field_filters() == [
        ('field', 'status')
    ]


def test_searches_parsers_params_parser_is_param(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&files.file_type=fastq&field=status'
    )
    p = ParamsParser(dummy_request)
    assert p.is_param(key='type', value='File')
    assert p.is_param(key='files.file_type', value='fastq')
    assert not p.is_param(key='files.file_type', value='bam')


def test_searches_parsers_params_parser_get_must_match_filter(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&files.file_type!=fastq&field=status'
    )
    p = ParamsParser(dummy_request)
    assert p.get_must_match_filters() == [
        ('type', 'Experiment'),
        ('type', 'File'),
        ('field', 'status')
    ]


def test_searches_parsers_params_parser_get_must_not_match_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type!=Experiment&type=File&files.file_type=fastq&field=status'
    )
    p = ParamsParser(dummy_request)
    assert p.get_must_not_match_filters() == [
        ('type!', 'Experiment')
    ]


def test_searches_parsers_params_parser_get_must_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&files.file_type!=fastq&field=status&type=*'
    )
    p = ParamsParser(dummy_request)
    assert p.get_must_filters() == [
        ('type', 'Experiment'),
        ('type', 'File'),
        ('field', 'status')
    ]


def test_searches_parsers_params_parser_get_must_not_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&files.file_type!=fastq'
        '&field=status&type=*&file_size!=*'
    )
    p = ParamsParser(dummy_request)
    assert p.get_must_not_filters() == [
        ('files.file_type!', 'fastq')
    ]


def test_searches_parsers_params_parser_get_exists_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&files.file_type!=fastq'
        '&field=status&type=*&file_size!=*'
    )
    p = ParamsParser(dummy_request)
    assert p.get_exists_filters() == [
        ('type', '*')
    ]


def test_searches_parsers_params_parser_get_not_exists_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=Experiment&type=File&files.file_type!=fastq'
        '&field=status&type=*&file_size!=*'
    )
    p = ParamsParser(dummy_request)
    assert p.get_not_exists_filters() == [
        ('file_size!', '*')
    ]


def test_searches_parsers_params_parser_chain_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type!=Experiment&type=File&files.file_type=fastq&field!=status'
    )
    p = ParamsParser(dummy_request)
    assert p.get_type_filters(params=p.get_must_not_match_filters()) == [
        ('type!', 'Experiment')
    ]
    assert p.get_must_not_match_filters(params=p.get_type_filters()) == [
        ('type!', 'Experiment')
    ]


def test_searches_parsers_params_parser_get_query_string(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=File&file_format%21=bigWig&file_type%21=bigBed+tss_peak'
        '&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert dummy_request.environ['QUERY_STRING'] == p.get_query_string()


def test_searches_parsers_params_parser_filter_and_query_string(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=File&file_format%21=bigWig&file_type%21=bigBed+tss_peak'
        '&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.get_type_filters() == [
        ('type', 'File')
    ]
    assert p.get_query_string(
        params=p.get_type_filters()
    ) == 'type=File'
    assert p.get_must_not_match_filters() == [
        ('file_format!', 'bigWig'),
        ('file_type!', 'bigBed tss_peak')
    ]
    assert p.get_query_string(
        params=p.get_must_not_match_filters()
    ) == 'file_format%21=bigWig&file_type%21=bigBed+tss_peak'
    assert p.get_must_match_filters() == [
        ('type', 'File'),
        ('file_format_type', 'bed3+')
    ]
    assert p.get_query_string(
        params=p.get_must_match_filters()
    ) == 'type=File&file_format_type=bed3%2B'
    assert dummy_request.environ['QUERY_STRING'] == p.get_query_string()


def test_searches_parsers_params_parser_filter_and_query_string_space(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=File&status=released&file_type=bed+bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.get_key_filters(
        key='file_type',
        params=p.get_must_match_filters()
    ) == [
        ('file_type', 'bed bed3+')
    ]
    assert p.get_search_term_filters() == []
    assert p.get_query_string(
        params=p.get_search_term_filters()
    ) == ''
    assert p.get_query_string(
        params=p.get_key_filters(key='file_type')
    ) == 'file_type=bed+bed3%2B'


def test_searches_parsers_params_parser_filtered_is_param(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=File&status=released&file_type=bed+bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.is_param('status', 'released')
    assert not p.is_param(
        'status',
        'released',
        params=p.get_type_filters()
    )
    assert p.is_param(
        'file_type',
        'bed bed3+',
        params=p.get_key_filters(
            key='file_type',
            params=p.get_must_match_filters()
        )
    )


def test_searches_parsers_params_parser_get_keys_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=File&file_format%21=bigWig&file_type%21=bigBed+tss_peak'
        '&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.get_keys_filters(['type', 'file_format_type']) == [
        ('type', 'File'),
        ('file_format_type', 'bed3+')
    ]
    assert p.get_keys_filters() == []


def test_searches_parsers_params_parser_get_not_keys_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&type=File&file_format%21=bigWig'
        '&file_type%21=bigBed+tss_peak&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.get_not_keys_filters(['type', 'file_format_type']) == [
        ('status', 'released'),
        ('file_format!', 'bigWig'),
        ('file_type!', 'bigBed tss_peak')
    ]
    assert p.get_not_keys_filters() == [
        ('status', 'released'),
        ('type', 'File'),
        ('file_format!', 'bigWig'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]


def test_searches_parsers_params_parser_get_wildcard_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&type=*&file_format%21=*'
        '&file_type%21=bigBed+tss_peak&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.get_wildcard_filters() == [
        ('type', '*'),
        ('file_format!', '*')
    ]


def test_searches_parsers_params_parser_get_not_wildcard_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&type=*&file_format%21=*'
        '&file_type%21=bigBed+tss_peak&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.get_not_wildcard_filters() == [
        ('status', 'released'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]


def test_searches_parsers_params_parser_remove_key_and_value_pair_from_filters(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&type=Biosample&type!=Experiment&type=*'
        '&file_format%21=*&file_type%21=bigBed+tss_peak'
        '&file_format_type=bed3%2B'
    )
    p = ParamsParser(dummy_request)
    assert p.remove_key_and_value_pair_from_filters(
        key='file_format!',
        value='*'
    ) == [
        ('status', 'released'),
        ('type', 'Biosample'),
        ('type!', 'Experiment'),
        ('type', '*'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]
    assert p.remove_key_and_value_pair_from_filters(
        key='status',
        value='released'
    ) == [
        ('type', 'Biosample'),
        ('type!', 'Experiment'),
        ('type', '*'),
        ('file_format!', '*'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]
    assert p.remove_key_and_value_pair_from_filters(
        key='type',
        value='Experiment'
    )== [
        ('status', 'released'),
        ('type', 'Biosample'),
        ('type!', 'Experiment'),
        ('type', '*'),
        ('file_format!', '*'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]
    assert p.remove_key_and_value_pair_from_filters(
        key='status',
        value='released'
    ) == [
        ('type', 'Biosample'),
        ('type!', 'Experiment'),
        ('type', '*'),
        ('file_format!', '*'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]
    assert p.remove_key_and_value_pair_from_filters(
        key='status!',
        value='released'
    ) == [
        ('status', 'released'),
        ('type', 'Biosample'),
        ('type!', 'Experiment'),
        ('type', '*'),
        ('file_format!', '*'),
        ('file_type!', 'bigBed tss_peak'),
        ('file_format_type', 'bed3+')
    ]
    with pytest.raises(ValueError):
        p.remove_key_and_value_pair_from_filters(key='type')
    with pytest.raises(ValueError):
        p.remove_key_and_value_pair_from_filters(value='*')


def test_searches_parsers_params_parser_keys_filters_not_flag(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&status!=submitted&type=File&file_format%21=bigWig'
    )
    p = ParamsParser(dummy_request)
    assert p.get_not_keys_filters() == [
        ('status', 'released'),
        ('status!', 'submitted'),
        ('type', 'File'),
        ('file_format!', 'bigWig')
    ]
    assert p.get_not_keys_filters(
        not_keys=['status']
    ) == [
        ('type', 'File'),
        ('file_format!', 'bigWig')
    ]
    assert p.get_not_keys_filters(
        not_keys=['status', 'file_format']
    ) == [
        ('type', 'File')
    ]
    assert p.get_not_keys_filters(
        not_keys=['status', 'file_format', 'type']
    ) == []
    assert p.get_keys_filters(
        keys=['status']
    ) == [
        ('status', 'released'),
        ('status!', 'submitted')
    ]
    assert p.get_keys_filters(
        keys=['status', 'file_format']
    ) == [
        ('status', 'released'),
        ('status!', 'submitted'),
        ('file_format!', 'bigWig')
    ]
    assert p.get_must_not_match_filters(
        params=p.get_keys_filters(
            keys=['status', 'file_format'])
    ) == [
        ('status!', 'submitted'),
        ('file_format!', 'bigWig')
    ]
    assert p.get_must_match_filters(
        params=p.get_keys_filters(
            keys=['status', 'file_format'])
    ) == [
        ('status', 'released')
    ]
    assert p.get_query_string(
        params=p.get_must_match_filters(
            params=p.get_keys_filters(
                keys=['status', 'file_format']
            )
        )
    ) == 'status=released'


def test_searches_parsers_params_parser_get_size(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&status!=submitted&type=File&file_format%21=bigWig'
    )
    p = ParamsParser(dummy_request)
    assert p.get_size() == []
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&status!=submitted&type=File'
        '&file_format%21=bigWig&size=100'
    )
    p = ParamsParser(dummy_request)
    assert p.get_size() == [
        ('size', '100')
    ]


def test_searches_parsers_params_parser_get_limit(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&status!=submitted&type=File&file_format%21=bigWig'
    )
    p = ParamsParser(dummy_request)
    assert p.get_limit() == []
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&status!=submitted&type=File'
        '&file_format%21=bigWig&limit=all'
    )
    p = ParamsParser(dummy_request)
    assert p.get_limit() == [
        ('limit', 'all')
    ]


def test_searches_parsers_params_parser_get_sort(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'status=released&status!=submitted&type=File&sort=date_created'
    )
    p = ParamsParser(dummy_request)
    assert p.get_sort() == [
        ('sort', 'date_created')
    ]


def test_searches_parsers_params_parser_get_frame(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'frame=embedded&status!=submitted&type=File&sort=date_created'
    )
    p = ParamsParser(dummy_request)
    assert p.get_frame() == [
        ('frame', 'embedded')
    ]


def test_searches_parsers_params_parser_param_keys_to_list(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'frame=embedded&status!=submitted&type=File&sort=date_created'
    )
    p = ParamsParser(dummy_request)
    assert p.param_keys_to_list() == [
        'frame',
        'status!',
        'type',
        'sort',
    ]


def test_searches_parsers_params_parser_param_values_to_list(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'frame=embedded&status!=submitted&type=File&sort=date_created'
    )
    p = ParamsParser(dummy_request)
    assert p.param_values_to_list() == [
        'embedded',
        'submitted',
        'File',
        'date_created',
    ]


def test_searches_parsers_params_parser_param_remove_not_flag(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'frame=embedded&status!=submitted&type=File&sort=date_created'
    )
    p = ParamsParser(dummy_request)
    assert p.remove_not_flag() == [
        ('frame', 'embedded'),
        ('status', 'submitted'),
        ('type', 'File'),
        ('sort', 'date_created')
    ]


def test_searches_parsers_params_parser_params_to_list(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'frame=embedded&status!=submitted&type=File&sort=date_created'
    )
    p = ParamsParser(dummy_request)
    assert p.params_to_list(key=False) == [
        'embedded',
        'submitted',
        'File',
        'date_created',
    ]
    assert p.params_to_list(key=True) == [
        'frame',
        'status!',
        'type',
        'sort',
    ]


def test_searches_parsers_params_parser_group_values_by_key(dummy_request):
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=*&status=released&status!=submitted&type=File&file_size=*'
        '&file_format%21=bigWig&restricted!=*&no_file_available!=*&limit=all'
        '&status=archived&status=revoked&file_format!=fastq'
    )
    p = ParamsParser(dummy_request)
    values_by_key = p.group_values_by_key()
    assert values_by_key == {
        'file_format!': ['bigWig', 'fastq'],
        'file_size': ['*'],
        'limit': ['all'],
        'no_file_available!': ['*'],
        'restricted!': ['*'],
        'status': ['released', 'archived', 'revoked'],
        'status!': ['submitted'],
        'type': ['*', 'File']
    }


def test_searchers_parsers_params_parser_split_filters_by_must_and_exists(dummy_request):
    from snovault.elasticsearch.searches.defaults import NOT_FILTERS
    from snovault.elasticsearch.searches.parsers import ParamsParser
    dummy_request.environ['QUERY_STRING'] = (
        'type=*&status=released&status!=submitted&type=File&file_size=*'
        '&file_format%21=bigWig&restricted!=*&no_file_available!=*&limit=all'
    )
    p = ParamsParser(dummy_request)
    must, must_not, exists, not_exists = p.split_filters_by_must_and_exists(
        params=p.get_not_keys_filters(not_keys=NOT_FILTERS) + p.get_type_filters()
    )
    assert must == [
        ('status', 'released'),
        ('type', 'File')
    ]
    assert must_not == [
        ('status!', 'submitted'),
        ('file_format!', 'bigWig')
    ]
    assert exists == [
        ('file_size', '*'),
        ('type', '*')
    ]
    assert not_exists == [
        ('restricted!', '*'),
        ('no_file_available!', '*')
    ]
