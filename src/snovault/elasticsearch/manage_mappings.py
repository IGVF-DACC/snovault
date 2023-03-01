from pyramid.paster import get_app

from pyramid.router import Router

from webtest import TestApp

from opensearchpy import OpenSearch

from opensearchpy.exceptions import NotFoundError

from dataclasses import dataclass

from .create_mapping import generate_indices_and_mappings
from .create_mapping import index_settings as get_index_settings
from .create_mapping import create_and_set_index_mapping

from .interfaces import ELASTIC_SEARCH
from .interfaces import RESOURCES_INDEX as ALL_RESOURCES_ALIAS

from typing import Any
from typing import Dict
from typing import Literal


@dataclass
class ManageMappingsProps:
    app: Router
    opensearch_client: OpenSearch
    type_alias_to_current_index_name: Dict[str, Any]
    mappings: Dict[str, Any]
    all_resources_alias: str
    should_reindex: Literal['always', 'never', 'after-initial']


def reindex_by_collection(app, collection):
    environ = {
        'HTTP_ACCEPT': 'application/json',
        'REMOTE_USER': 'INDEXER',
    }
    testapp = TestApp(
        app,
        environ
    )
    testapp.post_json(
        f'/_reindex_by_collection?collection={collection}',
        {},
    )


def get_aliases(props: ManageMappingsProps, type_alias):
    return {
        type_alias: {},
        props.all_resources_alias: {},
    }


def create_index(props: ManageMappingsProps, type_alias, current_index_name):
    print(f'Creating index {current_index_name} for type {type_alias}')
    index_settings = get_index_settings()
    index_settings['aliases'] = get_aliases(
        props,
        type_alias
    )
    create_and_set_index_mapping(
        es=props.opensearch_client,
        index=current_index_name,
        index_settings=index_settings,
        mapping=props.mappings[type_alias],
    )


def reindex_collections(app, collections):
    for collection in collections:
        print('Reindexing', collection)
        reindex_by_collection(
            app,
            collection,
        )


def clean_up_auto_created_indices(props: ManageMappingsProps):
    # We can't turn off auto_create_index at cluster level so we'll clean up manually
    # if any of our workers start writing to an index that doesn't exist yet.
    current_index_names = get_current_index_names(
        props.type_alias_to_current_index_name
    )
    try:
        all_existing_resources_indices = list(
            props.opensearch_client.indices.get_alias(
                props.all_resources_alias
            ).keys()
        )
    except NotFoundError as e:
        print(e)
        # Give up if resources alias doesn't exist yet.
        return
    for current_index_name in current_index_names:
        if current_index_name in all_existing_resources_indices:
            # It's aliased so we created it.
            continue
        if props.opensearch_client.indices.exists(current_index_name):
            # It exists but we didn't create it.
            print('Deleting unaliased (autocreated?) index', current_index_name)
            print(props.opensearch_client.indices.delete(current_index_name))


def should_reindex_collection(props: ManageMappingsProps, type_alias):
    if props.should_reindex == 'never':
        return False
    elif props.should_reindex == 'always':
        return True
    elif props.should_reindex == 'after-initial':
        try:
            return len(props.opensearch_client.indices.get_alias(type_alias)) > 0
        except Exception:
            return False


def create_latest_indices_and_reindex(props: ManageMappingsProps):
    collections_to_reindex = []
    for type_alias, current_index_name in props.type_alias_to_current_index_name.items():
        if not props.opensearch_client.indices.exists(current_index_name):
            # Check before creating new index.
            if should_reindex_collection(props, type_alias):
                collections_to_reindex.append(type_alias)
            create_index(
                props=props,
                type_alias=type_alias,
                current_index_name=current_index_name,
            )
        else:
            print(f'Index {current_index_name} for {type_alias} already exists')
    reindex_collections(props.app, collections_to_reindex)


def get_current_index_names(type_alias_to_current_index_name):
    return [
        current_index_name
        for type_alias, current_index_name in type_alias_to_current_index_name.items()
    ]


def delete_old_indices_if_empty(props: ManageMappingsProps):
    current_index_names = get_current_index_names(
        props.type_alias_to_current_index_name
    )
    all_existing_resources_indices = list(
        props.opensearch_client.indices.get_alias(
            props.all_resources_alias
        ).keys()
    )
    for existing_index in all_existing_resources_indices:
        if existing_index in current_index_names:
            print(f'Not deleting current index {existing_index}')
            continue
        documents_in_index = props.opensearch_client.count(index=existing_index)['count']
        if documents_in_index != 0:
            print(f'{existing_index} is not latest but still has documents, skipping delete')
            continue
        print(f'Deleting {existing_index}')
        print(props.opensearch_client.indices.delete(index=existing_index, ignore=[400, 404]))


def update(props: ManageMappingsProps):
    clean_up_auto_created_indices(props)
    create_latest_indices_and_reindex(props)
    delete_old_indices_if_empty(props)


def make_type_alias_to_current_index_name(app):
    mapping_hashes = app.registry['MAPPING_HASHES']
    return {
        k: f'{k}_{v}'
        for k, v in mapping_hashes.items()
    }


def get_mappings(app):
    indices, mappings = generate_indices_and_mappings(app)
    return mappings


def manage_mappings(app, should_reindex='never'):
    props = ManageMappingsProps(
        app=app,
        opensearch_client=app.registry[ELASTIC_SEARCH],
        type_alias_to_current_index_name=make_type_alias_to_current_index_name(app),
        mappings=get_mappings(app),
        all_resources_alias=ALL_RESOURCES_ALIAS,
        should_reindex=should_reindex
    )
    update(props)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Manage Opensearch mappings',
    )
    parser.add_argument(
        '--app-name',
        help='Pyramid app name in configfile'
    )
    parser.add_argument(
        'config_uri',
        help='path to configfile'
    )
    parser.add_argument(
        '--should-reindex',
        help='Controls reindexing behavior after creating new index',
        choices=[
            'always',
            'never',
            'after-initial',
        ],
        default='always',
    )
    args = parser.parse_args()
    app = get_app(
        args.config_uri,
        args.app_name
    )
    manage_mappings(app, args.should_reindex)


if __name__ == '__main__':
    main()