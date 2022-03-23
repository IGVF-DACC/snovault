from snovault.schema_utils import validate
import pytest


targets = [
    {'name': 'one', 'uuid': '775795d3-4410-4114-836b-8eeecf1d0c2f'},
]


@pytest.fixture
def content(testapp):
    url = '/testing-link-targets/'
    for item in targets:
        testapp.post_json(url, item, status=201)


def test_uniqueItems_validates_normalized_links(content, threadlocals):
    schema = {
        'properties': {
            'some_links': {
                'uniqueItems': True,
                'items': {
                    'linkTo': 'TestingLinkTarget',
                }
            }
        }
    }
    uuid = targets[0]['uuid']
    data = [
        uuid,
        '/testing-link-targets/{}'.format(uuid),
    ]
    validated, errors = validate(schema, {'some_links': data})
    assert len(errors) == 1
    assert (
        errors[0].message == "['{}', '{}'] has non-unique elements".format(
            uuid, uuid)
    )


def test_schema_utils_resolve_refs_returns_copy_of_original_if_no_refs(mocker):
    from snovault.schema_utils import resolve_refs
    resolver = None
    data = {'a': 'b'}
    resolved_data = resolve_refs(data, resolver)
    assert resolved_data == data
    assert id(resolved_data) != id(data)
    data = {
        'a': 'b',
        'c': ['d', 'e', 1],
        'x': {
            'y': {
                'z': [
                    {
                        'p': 'r'
                    },
                    3.2,
                    True,
                    False,
                    None
                ]
            }
        }
    }
    resolved_data = resolve_refs(data, resolver)
    assert resolved_data == data
    # Dicts are copies.
    assert id(resolved_data) != id(data)
    # Lists are copies.
    assert id(resolved_data['x']['y']['z'][0]) != id(data['x']['y']['z'][0])
    # Assignment doesn't reflect in original.
    resolved_data['x']['y']['z'][0]['p'] = 'new value'
    assert data['x']['y']['z'][0]['p'] == 'r'
    data = [
        'k',
        '5',
        '6',
        2,
        {},
    ]
    resolved_data = resolve_refs(data, resolver)
    assert resolved_data == data
    assert id(resolved_data) != id(data)


def test_schema_utils_resolve_refs_fills_in_refs(mocker):
    from snovault.schema_utils import resolve_refs
    resolver = None
    data = {'a': 'b'}
    resolved_data = resolve_refs(data, resolver)
    assert resolved_data == data
    resolve_ref = mocker.patch('snovault.schema_utils.resolve_ref')
    resolve_ref.return_value = {'a new value': 'that was resolved'}
    data = {'a': 'b', 'c': {'$ref': 'xyz'}}
    resolved_data = resolve_refs(data, resolver)
    expected_data = {'a': 'b', 'c': {'a new value': 'that was resolved'}}
    assert resolved_data == expected_data
    data = {
        'a': 'b',
        'c': {'$ref': 'xyz'},
        'sub': {
            'values': [
                'that',
                'were',
                'resolved',
                {
                    'if': {
                        '$ref': 'xyz',
                        'and': 'other',
                        'values': 'are',
                        'allowed': 'too',
                    }
                }
            ]
        }
    }
    resolved_data = resolve_refs(data, resolver)
    expected_data = {
        'a': 'b',
        'c': {'a new value': 'that was resolved'},
        'sub': {
            'values': [
                'that',
                'were',
                'resolved',
                {
                    'if': {
                        'a new value': 'that was resolved',
                        'and': 'other',
                        'values': 'are',
                        'allowed': 'too',
                    }
                }
            ]
        }
    }
    def custom_resolver(ref, resolver):
        if ref == 'xyz':
            return {
                'a': 'new value',
                'and': 'a ref',
                'inside': 'of a ref',
                '$ref': 'notxyz',
            }
        else:
            return {
                'the': 'notxyz values',
                'with': {
                    'sub': 'dependencies',
                    'and': ['lists'],
                }
            }
    resolve_ref.side_effect = custom_resolver
    data = {
        'something_new': [
            {
                '$ref': 'notxyz'
            }
        ],
        'a': 'b',
        'c': {'$ref': 'xyz'},
        'sub': {
            'values': [
                'that',
                'were',
                'resolved',
                {
                    'if': {
                        '$ref': 'xyz',
                        'and': 'other',
                        'values': 'are',
                        'allowed': 'too',
                    }
                }
            ]
        }
    }
    resolved_data = resolve_refs(data, resolver)
    expected_data = {
        'something_new': [
            {
                'the': 'notxyz values',
                'with': {
                    'sub': 'dependencies',
                    'and': ['lists']
                }
            }
        ],
        'a': 'b',
        'c': {
            'a': 'new value',
            'and': 'a ref',
            'inside': 'of a ref',
            'the': 'notxyz values',
            'with': {
                'sub': 'dependencies',
                'and': ['lists']
            }
        },
        'sub': {
            'values': [
                'that', 'were',
                'resolved', {
                    'if': {
                        'a': 'new value',
                        'and': 'other',
                        'inside': 'of a ref',
                        'the': 'notxyz values',
                        'with': {
                            'sub': 'dependencies',
                            'and': ['lists']
                        },
                        'values': 'are',
                        'allowed': 'too'
                    }
                }
            ]
        }
    }
    assert resolved_data == expected_data


def test_schema_utils_resolve_refs_fills_allows_override_of_ref_property(mocker):
    from snovault.schema_utils import resolve_refs
    resolver = None
    resolve_ref = mocker.patch('snovault.schema_utils.resolve_ref')
    resolve_ref.return_value = {
        'a new value': 'that was resolved',
        'custom': 'original value',
        'and': 'something else',
    }
    data = {
        'a': {
            '$ref': 'xyz',
            'custom': 'override',
        }
    }
    resolved_data = resolve_refs(data, resolver)
    expected_data = {
        'a': {
            'a new value': 'that was resolved',
            'and': 'something else',
            'custom': 'override',
        }
    }
    assert resolved_data == expected_data


def test_schema_utils_resolve_ref_in_real_schema():
    import codecs
    import json
    from pyramid.path import AssetResolver
    from snovault.schema_utils import resolve_ref
    from snovault.schema_utils import resolve_refs
    from jsonschema import RefResolver
    filename = 'snowflakes:schemas/snowball.json'
    utf8 = codecs.getreader('utf-8')
    asset = AssetResolver(
        'snowflakes'
    ).resolve(
        filename
    )
    schema = json.load(
        utf8(
            asset.stream()
        ),
        object_pairs_hook=dict
    )
    assert list(schema['properties'].keys()) == [
        'schema_version',
        'method'
    ]
    resolver = RefResolver('file://' + asset.abspath(), schema)

    # Try resolving ref from mixins.
    resolved = resolve_ref(
        'mixins.json#/uuid',
        resolver
    )
    assert resolved == {
        'uuid': {
            'title': 'UUID',
            'type': 'string',
            'format': 'uuid',
            'serverDefault': 'uuid4',
            'requestMethod': ['POST']
        }
    }
    # Resolve the inner object.
    resolved = resolve_ref(
        'mixins.json#/uuid/uuid',
        resolver
    )
    assert resolved == {
        'title': 'UUID',
        'type': 'string',
        'format': 'uuid',
        'serverDefault': 'uuid4',
        'requestMethod': ['POST']
    }
    # Raise error if resolve value not dict.
    with pytest.raises(ValueError) as error:
        resolved = resolve_ref(
            'mixins.json#/uuid/uuid/title',
            resolver
        )
    assert str(error.value) == (
        "Schema ref mixins.json#/uuid/uuid/title must resolve dict, not <class 'str'>"
    )
    # Add ref to properties.
    schema['properties']['accession'] = {
        '$ref': 'mixins.json#/accession/accession'
    }
    # Resolve from properties.
    resolved = resolve_refs(schema['properties'], resolver)
    expected = {
        'schema_version': {
            'default': '2', 'comment': 'For testing upgrades'
        },
        'method': {
            'title': 'Method',
            'description': 'Technique used to make snowball.',
            'type': 'string',
            'default': 'hand-packed',
            'enum': [
                'hand-packed',
                'scoop-formed',
                'accreted'
            ]
        },
        'accession': {
            'title': 'Accession',
            'description': 'A unique identifier to be used to reference the object prefixed with a db specific char set',
            'comment': 'Do not submit. The accession is assigned by the server.',
            'type': 'string',
            'format': 'accession',
            'serverDefault': 'accession',
            'permission': 'import_items'
        }
    }
    assert resolved == expected
    # Fill in status from top level
    del schema['properties']['accession']
    schema['properties']['$ref'] = 'mixins.json#/standard_status'
    resolved = resolve_refs(schema['properties'], resolver)
    expected = {
        'schema_version': {
            'default': '2',
            'comment': 'For testing upgrades'
        },
        'method': {
            'title': 'Method',
            'description': 'Technique used to make snowball.',
            'type': 'string',
            'default': 'hand-packed',
            'enum': [
                'hand-packed',
                'scoop-formed',
                'accreted'
            ]
        },
        'status': {
            'title': 'Status',
            'type': 'string',
            'default': 'in progress',
            'enum': [
                'in progress',
                'deleted',
                'replaced',
                'released'
            ]
        }
    }
    assert resolved == expected
