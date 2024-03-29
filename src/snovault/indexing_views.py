from pyramid.security import (
    principals_allowed_by_permission,
)
from pyramid.authorization import (
    Authenticated,
    Everyone
)
from pyramid.traversal import resource_path
from pyramid.view import view_config
from .resources import Item


def includeme(config):
    config.scan(__name__, categories=None)
    config.add_route('opensearch-item-type-to-index-name', '/opensearch-item-type-to-index-name{slash:/?}')


@view_config(context=Item, name='index-data', permission='index', request_method='GET')
def item_index_data(context, request):
    uuid = str(context.uuid)
    properties = context.upgrade_properties()
    links = context.links(properties)
    unique_keys = context.unique_keys(properties)

    principals_allowed = {}
    for permission in ('view', 'edit', 'audit'):
        principals = principals_allowed_by_permission(context, permission)
        if principals is Everyone:
            principals = [Everyone]
        elif Everyone in principals:
            principals = [Everyone]
        elif Authenticated in principals:
            principals = [Authenticated]
        # Filter our roles
        principals_allowed[permission] = [
            p for p in sorted(principals) if not p.startswith('role.')
        ]

    path = resource_path(context)
    paths = {path}
    collection = context.collection

    if collection.unique_key in unique_keys:
        paths.update(
            resource_path(collection, key)
            for key in unique_keys[collection.unique_key])

    for base in (collection, request.root):
        for key_name in ('accession', 'alias'):
            if key_name not in unique_keys:
                continue
            paths.add(resource_path(base, uuid))
            paths.update(
                resource_path(base, key)
                for key in unique_keys[key_name])

    path = path + '/'
    embedded = request.embed(path, '@@embedded')
    object = request.embed(path, '@@object')

    audit = request.embed(path, '@@audit')['audit']

    item_type = context.type_info.item_type

    item_type_to_index_name = request.registry['OPENSEARCH_ITEM_TYPE_TO_INDEX_NAME']

    index_name = item_type_to_index_name[item_type]

    document = {
        'audit': audit,
        'embedded': embedded,
        'embedded_uuids': sorted(request._embedded_uuids),
        'item_type': item_type,
        'index_name': index_name,
        'linked_uuids': sorted(request._linked_uuids),
        'links': links,
        'object': object,
        'paths': sorted(paths),
        'principals_allowed': principals_allowed,
        'properties': properties,
        'propsheets': {
            name: context.propsheets[name]
            for name in context.propsheets.keys() if name != ''
        },
        'tid': context.tid,
        'unique_keys': unique_keys,
        'uuid': uuid,
    }

    return document


@view_config(context=Item, name='index-data-external', permission='index', request_method='GET')
def item_index_data_external(context, request):
    request.datastore = 'database'
    uuid = str(context.uuid)
    return request.embed(
        f'/{uuid}/@@index-data',
        as_user='INDEXER',
    )


@view_config(route_name='opensearch-item-type-to-index-name', request_method='GET', permission='search')
def opensearch_mapping_hashes(context, request):
    return request.registry['OPENSEARCH_ITEM_TYPE_TO_INDEX_NAME']
