from pyramid.view import view_config

from snovault.interfaces import COLLECTIONS
from snovault.interfaces import DBSESSION

from snoindex.domain.message import OutboundMessage


def includeme(config):
    config.add_route('_reindex', '/_reindex')
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
    print(make_unique_id(uuid, xid))
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


def put_uuids_on_invalidaiton_queue(request):
    xmin = get_current_xmin(request)
    invalidation_queue = request.registry['INVALIDATION_QUEUE']
    outbound_messages = [
        make_outbound_message(uuid, xmin)
        for uuid in get_all_uuids(request)
    ]
    invalidation_queue.send_messages(
        outbound_messages
    )


@view_config(
    route_name='_reindex',
    request_method='POST',
    permission='index'
)
def reindex_view(request):
    put_uuids_on_invalidaiton_queue(request)
