from pyramid.paster import get_app

from webtest import TestApp

from opensearchpy.exceptions import NotFoundError

from .create_mapping import generate_indices_and_mappings
from .create_mapping import index_settings as get_index_settings
from .create_mapping import create_and_set_index_mapping

from .interfaces import ELASTIC_SEARCH
from .interfaces import RESOURCES_INDEX as ALL_RESOURCES_ALIAS


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


def get_aliases(type_alias, all_resources_alias=ALL_RESOURCES_ALIAS):
    return {
        type_alias: {},
        all_resources_alias: {},
    }


def create_index(opensearch_client, type_alias, current_index_name, mappings):
    print(f'Creating index {current_index_name} for type {type_alias}')
    index_settings = get_index_settings()
    index_settings['aliases'] = get_aliases(type_alias)
    create_and_set_index_mapping(
        es=opensearch_client,
        index=current_index_name,
        index_settings=index_settings,
        mapping=mappings[type_alias],
    )


def reindex_collections(app, collections):
    for collection in collections:
        print('Reindexing', collection)
        reindex_by_collection(
            app,
            collection,
        )


def clean_up_auto_created_indices(opensearch_client, type_alias_to_current_index_name, all_resources_alias=ALL_RESOURCES_ALIAS):
    # We can't turn off auto_create_index at cluster level so we'll clean up manually
    # if any of our workers start writing to an index that doesn't exist yet.
    current_index_names = get_current_index_names(
        type_alias_to_current_index_name
    )
    try:
        all_existing_resources_indices = list(
            opensearch_client.indices.get_alias(
                all_resources_alias
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
        if opensearch_client.indices.exists(current_index_name):
            # It exists but we didn't create it.
            print('Deleting unaliased (autocreated?) index', current_index_name)
            print(opensearch_client.indices.delete(current_index_name))


def create_latest_indices_and_reindex(app, opensearch_client, type_alias_to_current_index_name, mappings):
    collections_to_reindex = []
    for type_alias, current_index_name in type_alias_to_current_index_name.items():
        if not opensearch_client.indices.exists(current_index_name):
            create_index(
                opensearch_client=opensearch_client,
                type_alias=type_alias,
                current_index_name=current_index_name,
                mappings=mappings,
            )
            collections_to_reindex.append(type_alias)
        else:
            print(f'Index {current_index_name} for {type_alias} already exists')
    reindex_collections(app, collections_to_reindex)


def get_current_index_names(type_alias_to_current_index_name):
    return [
        current_index_name
        for type_alias, current_index_name in type_alias_to_current_index_name.items()
    ]


def delete_old_indices_if_empty(opensearch_client, type_alias_to_current_index_name, all_resources_alias=ALL_RESOURCES_ALIAS):
    current_index_names = get_current_index_names(
        type_alias_to_current_index_name
    )
    all_existing_resources_indices = list(
        opensearch_client.indices.get_alias(
            all_resources_alias
        ).keys()
    )
    for existing_index in all_existing_resources_indices:
        if existing_index in current_index_names:
            print(f'Not deleting current index {existing_index}')
            continue
        documents_in_index = opensearch_client.count(index=existing_index)['count']
        if documents_in_index != 0:
            print(f'{existing_index} is not latest but still has documents, skipping delete')
            continue
        print(f'Deleting {existing_index}')
        print(opensearch_client.indices.delete(index=existing_index, ignore=[400, 404]))


def update(app, opensearch_client, type_alias_to_current_index_name, mappings):
    clean_up_auto_created_indices(
        opensearch_client=opensearch_client,
        type_alias_to_current_index_name=type_alias_to_current_index_name,
    )
    create_latest_indices_and_reindex(
        app=app,
        opensearch_client=opensearch_client,
        type_alias_to_current_index_name=type_alias_to_current_index_name,
        mappings=mappings,
    )
    delete_old_indices_if_empty(
        opensearch_client=opensearch_client,
        type_alias_to_current_index_name=type_alias_to_current_index_name,
    )


def make_type_alias_to_current_index_name(app):
    mapping_hashes = app.registry['MAPPING_HASHES']
    return {
        k: f'{k}_{v}'
        for k, v in mapping_hashes.items()
    }


def get_mappings(app):
    indices, mappings = generate_indices_and_mappings(app)
    return mappings


def manage_mappings(app):
    opensearch_client = app.registry[ELASTIC_SEARCH]
    type_alias_to_current_index_name = make_type_alias_to_current_index_name(
        app
    )
    mappings = get_mappings(app)
    opensearch_client = app.registry[ELASTIC_SEARCH]
    update(
        app,
        opensearch_client,
        type_alias_to_current_index_name,
        mappings,
    )


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
    args = parser.parse_args()
    app = get_app(
        args.config_uri,
        args.app_name
    )
    manage_mappings(app)


if __name__ == '__main__':
    main()
