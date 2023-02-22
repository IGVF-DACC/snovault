from pyramid.view import view_config

from pyramid.httpexceptions import HTTPBadRequest

from snovault.interfaces import COLLECTIONS
from snovault.interfaces import DBSESSION

from snoindex.domain.message import OutboundMessage

from typing import Any
from typing import Dict


def includeme(config):
    config.add_route('_reindex', '/_reindex')
    config.add_route('_reindex_by_collection', '/_reindex_by_collection')
    config.add_route('indexer_info', '/indexer-info')
    config.scan(__name__)


def get_all_uuids(request, types=None):
    # First index user and access_key so people can log in
    collections = request.registry[COLLECTIONS]
    initial = ['user', 'access_key']
    for collection_name in initial:
        # for snovault test application, there are no users or keys
        if types is not None and collection_name not in types:
            continue
        collection = collections.by_item_type.get(collection_name, [])
        for uuid in collection:
            yield str(uuid)
    for collection_name in sorted(collections.by_item_type):
        if collection_name in initial:
            continue
        if types is not None and collection_name not in types:
            continue
        collection = collections.by_item_type[collection_name]
        for uuid in collection:
            yield str(uuid)


def get_all_uuids_in_collection(request, collection):
    return get_all_uuids(request, types=[collection])


def get_current_xmin(request):
    session = request.registry[DBSESSION]()
    connection = session.connection()
    query = connection.execute(
        'SELECT pg_snapshot_xmin(pg_current_snapshot());'
    )
    xmin = query.scalar()
    return xmin


def make_unique_id(uuid: str, xid: str) -> str:
    return f'{uuid}-{xid}'


def make_outbound_message(uuid: str, xid: str) -> OutboundMessage:
    body = {
        'metadata': {
            'xid': xid,
        },
        'data': {
            'uuid': uuid,
        }
    }
    outbound_message = OutboundMessage(
        unique_id=make_unique_id(uuid, xid),
        body=body,
    )
    return outbound_message


def _put_uuids_on_invalidation_queue(request, uuids):
    xmin = get_current_xmin(request)
    invalidation_queue = request.registry['INVALIDATION_QUEUE']
    outbound_messages = [
        make_outbound_message(uuid, xmin)
        for uuid in uuids
    ]
    invalidation_queue.send_messages(
        outbound_messages
    )


def put_uuids_on_invalidaiton_queue(request):
    _put_uuids_on_invalidation_queue(
        request=request,
        uuids=get_all_uuids(request)
    )


def put_collection_uuids_on_invalidaiton_queue(request, collection):
    _put_uuids_on_invalidation_queue(
        request=request,
        uuids=get_all_uuids_in_collection(
            request,
            collection,
        )
    )


@view_config(
    route_name='_reindex',
    request_method='POST',
    permission='index'
)
def reindex_view(request):
    put_uuids_on_invalidaiton_queue(request)


@view_config(
    route_name='_reindex_by_collection',
    request_method='POST',
    permission='index'
)
def reindex_by_collection_view(request):
    requested_collection = request.params.get('collection')
    actual_collections = list(
        request.registry[COLLECTIONS].by_item_type.keys()
    )
    if requested_collection not in actual_collections:
        raise HTTPBadRequest(
            detail=f'{requested_collection} invalid collection name'
        )
    put_collection_uuids_on_invalidaiton_queue(request, requested_collection)


def get_approximate_numbers_from_queue(info: Dict[str, Any]):
    queue_info_fields_to_include = [
        'ApproximateNumberOfMessages',
        'ApproximateNumberOfMessagesNotVisible',
        'ApproximateNumberOfMessagesDelayed',
    ]
    return {
        k: int(v)
        for k, v in info.items()
        if k in queue_info_fields_to_include
    }


def is_indexing(indexer_info: Dict[str, Any]) -> bool:
    return any(
        (
            indexer_info['transaction_queue']['ApproximateNumberOfMessages'] > 0,
            indexer_info['invalidation_queue']['ApproximateNumberOfMessages'] > 0,
        )
    )


@view_config(
    route_name='indexer_info',
    request_method='GET',
)
def indexer_info_view(request):
    transaction_queue = request.registry['TRANSACTION_QUEUE']
    invalidation_queue = request.registry['INVALIDATION_QUEUE']
    indexer_info = {
        'transaction_queue': get_approximate_numbers_from_queue(
            transaction_queue.info()
        ),
        'invalidation_queue': get_approximate_numbers_from_queue(
            invalidation_queue.info()
        ),
    }
    indexer_info['is_indexing'] = is_indexing(
        indexer_info
    )
    return indexer_info
