import requests
import time

from dataclasses import dataclass

from opensearchpy import OpenSearch
from opensearch_dsl import Search

from snovault.remote.queue import SQSQueue
from snovault.remote.queue import SQSQueueProps
from snovault.remote.queue import OutboundMessage
from snovault.remote.queue import client
from snovault.remote.queue import TRANSACTION_QUEUE_URL
from snovault.remote.queue import INVALIDATION_QUEUE_URL

from snovault.elasticsearch.interfaces import RESOURCES_INDEX


auth = ('foobar', 'bazqux')
url = 'http://nginx:8000'
OPENSEARCH_URL = 'http://opensearch:9200'
opensearch_client = OpenSearch(
    OPENSEARCH_URL
)


transaction_queue = SQSQueue(
    props=SQSQueueProps(
        client=client,
        queue_url=TRANSACTION_QUEUE_URL,
    )
)

transaction_queue.wait_for_queue_to_exist()

invalidation_queue = SQSQueue(
    props=SQSQueueProps(
        client=client,
        queue_url=INVALIDATION_QUEUE_URL,
    )
)

invalidation_queue.wait_for_queue_to_exist()


def get_related_uuids_from_updated_and_renamed(updated, renamed):
    query = {
        'query': {
            'bool': {
                'should': [
                    {
                        'terms': {
                            'embedded_uuids': updated,
                        },
                    },
                    {
                        'terms': {
                            'linked_uuids': renamed,
                        },
                    },
                ],
            },
        },
        '_source': False,
    }
    search = Search(
        using=opensearch_client,
        index=RESOURCES_INDEX,
    )
    search = search.update_from_dict(
        query
    ).params(
        request_timeout=60,
    )
    for hit in search.scan():
        yield hit.meta.id


def get_uuids_from_transaction(message):
    uuids = set()
    payload = message.json_body['data']['payload']
    uuids.update(payload['updated'])
    uuids.update(payload['renamed'])
    return list(uuids)


def get_all_uuids_from_transaction(messages):
    uuids = set()
    for message in messages:
        uuids.update(
            get_uuids_from_transaction(message)
        )
    return uuids


def get_updated_uuids_from_transaction(message):
    payload = message.json_body['data']['payload']
    return payload['updated']


def get_renamed_uuids_from_transaction(message):
    payload = message.json_body['data']['payload']
    return payload['renamed']


def make_unique_id(uuid, xid):
    return f'{uuid}-{xid}'


def make_outbound_message(message, uuid):
    xid = message.json_body['metadata']['xid']
    message = {
        'metadata': {
            'xid': xid,
            'tid': message.json_body['metadata']['tid'],
        },
        'data': {
            'uuid': uuid,
        }
    }
    outbound_message = OutboundMessage(
        unique_id=make_unique_id(uuid, xid),
        body=message,
    )
    return outbound_message


def invalidate_all_uuids_from_transactions(messages):
    outbound_messages = []
    for message in messages:
        uuids = get_uuids_from_transaction(message)
        for uuid in uuids:
            outbound_messages.append(
                make_outbound_message(
                    message,
                    uuid
                )
            )
    invalidation_queue.send_messages(
        outbound_messages
    )


def invalidate_all_related_uuids(messages):
    outbound_messages = []
    already_invalidated_uuids = get_all_uuids_from_transaction(messages)
    opensearch_client.indices.refresh(RESOURCES_INDEX)
    for message in messages:
        updated = get_updated_uuids_from_transaction(message)
        renamed = get_renamed_uuids_from_transaction(message)
        related_uuids = get_related_uuids_from_updated_and_renamed(
            updated,
            renamed
        )
        for uuid in related_uuids:
            if uuid in already_invalidated_uuids:
                continue
            outbound_messages.append(
                make_outbound_message(
                    message,
                    uuid
                )
            )
    invalidation_queue.send_messages(
        outbound_messages
    )


def handle_messages(messages):
    invalidate_all_uuids_from_transactions(messages)
    invalidate_all_related_uuids(messages)


def poll():
    print('LISTENING to transaction queue')
    number_of_handled_messages = 0
    while True:
        messages = list(
            transaction_queue.get_messages(
                desired_number_of_messages=1
            )
        )
        if messages:
            handle_messages(messages)
            transaction_queue.mark_as_processed(messages)
            number_of_handled_messages += len(messages)
            if number_of_handled_messages % 100 == 0:
                print(f'transaction queue messages handled so far: {number_of_handled_messages}')


if __name__ == '__main__':
    poll()