import hashlib

import json

import os

from pathlib import Path

from pyramid.paster import get_app

from snovault import AUDITOR
from snovault import COLLECTIONS
from snovault import CALCULATED_PROPERTIES

from snovault.elasticsearch.create_mapping import generate_indices_and_mappings


class UnexpectedMappingError(Exception):
    pass


def maybe_raise_on_diff(output_directory, filename, annotated_mapping, raise_on_diff):
    if not raise_on_diff:
        return
    filepath = Path(output_directory, filename).resolve()
    if not filepath.is_file():
        raise UnexpectedMappingError(
            f'{filepath} not found. Have you generated latest mappings?'
        )
    with open(filepath) as f:
        existing_mapping = json.load(f)
    for k, v in annotated_mapping.items():
        actual = existing_mapping.get(k)
        expected = v
        if actual != expected:
            raise UnexpectedMappingError(
                f'Found {k} {actual} in {filepath}, expected {expected}. Have you generated latest mappings?'
            )


def write_annotated_mappings(annotated_mappings, relative_output_directory, raise_on_diff):
    current_directory = os.getcwd()
    output_directory = Path(current_directory, relative_output_directory)
    for annotated_mapping in annotated_mappings:
        filename = f'{annotated_mapping["item_type"]}.json'
        maybe_raise_on_diff(
            output_directory=output_directory,
            filename=filename,
            annotated_mapping=annotated_mapping,
            raise_on_diff=raise_on_diff
        )
        with open(Path(output_directory, filename), 'w') as f:
            print(f'Writing {filename}')
            json.dump(
                annotated_mapping,
                f,
                sort_keys=True,
                indent=4,
            )
            # Always add newline at EOF.
            f.write('\n')


def annotate_mappings(indices, mappings, indices_hashes):
    annotated_mappings = []
    for index in indices:
        mapping = mappings[index]
        mapping_hash = indices_hashes[index].hexdigest()
        annotated_mappings.append(
            {
                'item_type': index,
                'hash': mapping_hash,
                'index_name': f'{index}_{mapping_hash[:8]}',
                'mapping': mapping,
            }
        )
    return annotated_mappings


def initialize_indices_hashes(app, indices):
    return {
        index: hashlib.md5()
        for index in indices
    }


def update_indices_hashes_with_calculated_properties(app, indices_hashes):
    collections = app.registry[COLLECTIONS]
    calculated_properties = app.registry[CALCULATED_PROPERTIES]
    for index in indices_hashes.keys():
        collection = collections.by_item_type[index]
        calculated_properties_for_item_type = calculated_properties.props_for(
            collection.type_info.factory
        )
        index_hash = indices_hashes[index]
        for name, calculated_property in sorted(calculated_properties_for_item_type.items()):
            # Hashes the name, bytecode, variable names, constants, and
            # defaults of a calculated_property function.
            index_hash.update(calculated_property.fn.__code__.co_name.encode('utf-8'))
            index_hash.update(calculated_property.fn.__code__.co_code)
            index_hash.update(str(calculated_property.fn.__code__.co_varnames).encode('utf-8'))
            index_hash.update(str(calculated_property.fn.__code__.co_consts).encode('utf-8'))
            index_hash.update(str(calculated_property.fn.__defaults__).encode('utf-8'))


def update_indices_hashes_with_audits(app, indices_hashes):
    collections = app.registry[COLLECTIONS]
    audits = app.registry[AUDITOR].type_checkers
    for index in indices_hashes.keys():
        collection = collections.by_item_type[index]
        item_types = [collection.type_info.name] + collection.type_info.base_types
        audits_for_item_types = set()
        audits_for_item_types.update(
            *(
                audits.get(item_type, ())
                for item_type in item_types
            )
        )
        index_hash = indices_hashes[index]
        for order, checker, condition, frame in sorted(audits_for_item_types):
            index_hash.update(frame.encode('utf-8'))
            index_hash.update(checker.__code__.co_name.encode('utf-8'))
            index_hash.update(checker.__code__.co_code)
            index_hash.update(str(checker.__code__.co_varnames).encode('utf-8'))
            index_hash.update(str(checker.__code__.co_consts).encode('utf-8'))
            index_hash.update(str(checker.__defaults__).encode('utf-8'))


def update_indices_hashes_with_mappings(app, indices_hashes, mappings):
    for index in indices_hashes:
        mapping = mappings[index]
        index_hash = indices_hashes[index]
        index_hash.update(
            json.dumps(
                mapping,
                sort_keys=True
            ).encode('utf-8')
        )


def generate_and_write_mappings(app, relative_output_directory, raise_on_diff=False):
    indices, mappings = generate_indices_and_mappings(app)
    indices_hashes = initialize_indices_hashes(app, indices)
    #update_indices_hashes_with_calculated_properties(app, indices_hashes)
    #update_indices_hashes_with_audits(app, indices_hashes)
    update_indices_hashes_with_mappings(app, indices_hashes, mappings)
    annotated_mappings = annotate_mappings(indices, mappings, indices_hashes)
    write_annotated_mappings(
        annotated_mappings=annotated_mappings,
        relative_output_directory=relative_output_directory,
        raise_on_diff=raise_on_diff
    )


def get_args():
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate Opensearch Mappings'
    )
    parser.add_argument(
        '--app-name',
        help='Pyramid app name in configfile'
    )
    parser.add_argument(
        '--relative-output-directory',
        help='Directory to write mappings'
    )
    parser.add_argument(
        'config_uri',
        help='path to configfile'
    )
    parser.add_argument(
        '--raise-on-diff',
        action='store_true'
    )
    return parser.parse_args()


def main():
    args = get_args()
    app = get_app(
        args.config_uri,
        args.app_name
    )
    generate_and_write_mappings(
        app=app,
        relative_output_directory=args.relative_output_directory,
        raise_on_diff=args.raise_on_diff,
    )


if __name__ == '__main__':
    main()
