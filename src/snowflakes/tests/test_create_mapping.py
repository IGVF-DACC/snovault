import pytest
from ..loadxl import ORDER


@pytest.mark.parametrize('item_type', ORDER)
def test_create_mapping(registry, item_type):
    from snovault.elasticsearch.create_mapping import type_mapping
    from snovault import TYPES
    mapping = type_mapping(registry[TYPES], item_type)
    assert mapping


def test_mapping_generate_indices_and_mappings(testapp, registry):
    from snovault.elasticsearch.create_mapping import generate_indices_and_mappings
    testapp.registry = registry
    indices, mappings = generate_indices_and_mappings(testapp)
    assert indices == [
        'award',
        'lab',
        'access_key',
        'image',
        'page',
        'snowball',
        'snowflake',
        'snowfort',
        'user',
        'testing_bad_accession',
        'testing_custom_embed_source',
        'testing_custom_embed_target',
        'testing_dependencies',
        'testing_download',
        'testing_link_source',
        'testing_link_target',
        'testing_post_put_patch',
        'testing_search_schema',
        'testing_search_schema_special_facets',
        'testing_server_default'
    ]
    assert list(mappings.keys()) == [
        'snovault',
        'award',
        'lab',
        'access_key',
        'image',
        'page',
        'snowball',
        'snowflake',
        'snowfort',
        'user',
        'testing_bad_accession',
        'testing_custom_embed_source',
        'testing_custom_embed_target',
        'testing_dependencies',
        'testing_download',
        'testing_link_source',
        'testing_link_target',
        'testing_post_put_patch',
        'testing_search_schema',
        'testing_search_schema_special_facets',
        'testing_server_default'
    ]
    assert mappings['award'] == {
        'dynamic_templates': [
            {
                'template_principals_allowed': {
                    'path_match': 'principals_allowed.*',
                    'match_mapping_type': 'string',
                    'mapping': {
                        'type': 'keyword'
                    }
                }
            },
            {
                'template_unique_keys': {
                    'path_match': 'unique_keys.*',
                    'match_mapping_type': 'string',
                    'mapping': {
                        'type': 'keyword',
                        'copy_to': '_all'
                    }
                }
            },
            {
                'template_links': {
                    'path_match': 'links.*',
                    'match_mapping_type': 'string',
                    'mapping': {
                        'type': 'keyword'
                    }
                }
            },
            {
                'strings': {
                    'match_mapping_type': 'string',
                    'mapping': {
                        'type': 'keyword'
                    }
                }
            },
            {
                'integers': {
                    'match_mapping_type': 'long',
                    'mapping': {
                        'type': 'long',
                        'fields': {
                            'raw': {
                                'type': 'keyword'
                            }
                        }
                    }
                }
            }
        ],
        'properties': {
            '_all': {
                'type': 'text',
                'store': False,
                'analyzer': 'snovault_index_analyzer',
                'search_analyzer': 'snovault_search_analyzer'
            },
            'uuid': {
                'type': 'keyword',
                'copy_to': '_all'
            },
            'tid': {
                'type': 'keyword'
            },
            'item_type': {
                'type': 'keyword',
                'copy_to': '_all'
            },
            'index_name': {
                'type': 'keyword',
            },
            'embedded': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'keyword'
                    },
                    'uuid': {
                        'type': 'keyword'
                    },
                    'schema_version': {
                        'type': 'keyword'
                    },
                    'title': {
                        'type': 'keyword',
                        'copy_to': '_all'
                    },
                    'name': {
                        'type': 'keyword',
                        'copy_to': '_all'
                    },
                    'description': {
                        'type': 'text'
                    },
                    'start_date': {
                        'type': 'keyword'
                    },
                    'end_date': {
                        'type': 'keyword'
                    },
                    'url': {
                        'type': 'keyword'
                    },
                    'pi': {
                        'type': 'object',
                        'properties': {
                            'status': {
                                'type': 'keyword'
                            },
                            'uuid': {
                                'type': 'keyword'
                            },
                            'schema_version': {
                                'type': 'keyword'
                            },
                            'email': {
                                'type': 'keyword'
                            },
                            'first_name': {
                                'type': 'keyword'
                            },
                            'last_name': {
                                'type': 'keyword'
                            },
                            'lab': {
                                'type': 'keyword'
                            },
                            'submits_for': {
                                'type': 'keyword'
                            },
                            'groups': {
                                'type': 'keyword'
                            },
                            'viewing_groups': {
                                'type': 'keyword'
                            },
                            'job_title': {
                                'type': 'keyword'
                            },
                            'phone1': {
                                'type': 'keyword'
                            },
                            'phone2': {
                                'type': 'keyword'
                            },
                            'fax': {
                                'type': 'keyword'
                            },
                            'skype': {
                                'type': 'keyword'
                            },
                            'google': {
                                'type': 'keyword'
                            },
                            'timezone': {
                                'type': 'keyword'
                            },
                            '@id': {
                                'type': 'keyword'
                            },
                            '@type': {
                                'type': 'keyword'
                            },
                            'title': {
                                'type': 'keyword',
                                'copy_to': '_all'
                            }
                        }
                    },
                    'rfa': {
                        'type': 'keyword'
                    },
                    'project': {
                        'type': 'keyword',
                        'copy_to': '_all'
                    },
                    'viewing_group': {
                        'type': 'keyword'
                    },
                    '@id': {
                        'type': 'keyword'
                    },
                    '@type': {
                        'type': 'keyword'
                    }
                }
            },
            'object': {
                'type': 'object',
                'enabled': False
            },
            'properties': {
                'type': 'object',
                'enabled': False
            },
            'propsheets': {
                'type': 'object',
                'enabled': False
            },
            'embedded_uuids': {
                'type': 'keyword'
            },
            'linked_uuids': {
                'type': 'keyword'
            },
            'paths': {
                'type': 'keyword'
            },
            'audit': {
                'type': 'object',
                'properties': {
                    'ERROR': {
                        'type': 'object',
                        'properties': {
                            'category': {
                                'type': 'keyword'
                            },
                            'detail': {
                                'type': 'text',
                                'index': 'true'
                            },
                            'level_name': {
                                'type': 'keyword'
                            },
                            'level': {
                                'type': 'integer'
                            }
                        }
                    },
                    'NOT_COMPLIANT': {
                        'type': 'object',
                        'properties': {
                            'category': {
                                'type': 'keyword'
                            },
                            'detail': {
                                'type': 'text',
                                'index': 'true'
                            },
                            'level_name': {
                                'type': 'keyword'
                            },
                            'level': {
                                'type': 'integer'
                            }
                        }
                    },
                    'WARNING': {
                        'type': 'object',
                        'properties': {
                            'category': {
                                'type': 'keyword'
                            },
                            'detail': {
                                'type': 'text',
                                'index': 'true'
                            },
                            'level_name': {
                                'type': 'keyword'
                            },
                            'level': {
                                'type': 'integer'
                            }
                        }
                    },
                    'INTERNAL_ACTION': {
                        'type': 'object',
                        'properties': {
                            'category': {
                                'type': 'keyword'
                            },
                            'detail': {
                                'type': 'text',
                                'index': 'true'
                            },
                            'level_name': {
                                'type': 'keyword'
                            },
                            'level': {
                                'type': 'integer'
                            }
                        }
                    }
                }
            }
        }
    }


def test_mapping_register_opensesarch_item_type_to_index_name_view(testapp):
    actual = testapp.get('/opensearch-item-type-to-index-name').json
    actual_keys = sorted(actual.keys())
    expected_keys = [
        'access_key',
        'award',
        'image',
        'lab',
        'page',
        'snowball',
        'snowflake',
        'snowfort',
        'testing_bad_accession',
        'testing_custom_embed_source',
        'testing_custom_embed_target',
        'testing_dependencies',
        'testing_download',
        'testing_link_source',
        'testing_link_target',
        'testing_post_put_patch',
        'testing_search_schema',
        'testing_search_schema_special_facets',
        'testing_server_default',
        'user'
    ]
    assert actual_keys == expected_keys
