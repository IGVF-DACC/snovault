import requests
import time

from opensearchpy import OpenSearch

from snovault.remote.queue import SQSQueue
from snovault.remote.queue import SQSQueueProps
from snovault.remote.queue import client
from snovault.remote.queue import INVALIDATION_QUEUE_URL


auth = ('foobar', 'bazqux')
url = 'http://pyramid:6543'
OPENSEARCH_URL = 'http://opensearch:9200'
opensearch_client = OpenSearch(
    OPENSEARCH_URL
)


def get_item(uuid):
    return requests.get(
        f'{url}/{uuid}/@@index-data-external/?datastore=database',
        auth=auth
    ).json()


def index_item(item, version):
    opensearch_client.index(
        index=item['item_type'],
        body=item,
        id=item['uuid'],
        request_timeout=30,
        version=version,
        version_type='external_gte',
    )


def get_uuid_and_version_from_message(message):
    uuid = message.json_body['data']['uuid']
    version = message.json_body['metadata']['xid']
    return (uuid, version)


def handle_messages(messages):
    for message in messages:
        uuid, version = get_uuid_and_version_from_message(message)
        item = get_item(uuid)
        print('got', item)
        index_item(item, version)


def get_invalidation_queue():
    invalidation_queue = SQSQueue(
        props=SQSQueueProps(
            client=client,
            queue_url=INVALIDATION_QUEUE_URL,
        )
    )
    invalidation_queue.wait_for_queue_to_exist()
    return invalidation_queue


def poll():
    number_of_handled_messages = 0
    invalidation_queue = get_invalidation_queue()
    print('LISTENING to invalidation queue')
    while True:
        messages = list(
            invalidation_queue.get_messages(
                desired_number_of_messages=10
            )
        )
        if messages:
            handle_messages(messages)
            invalidation_queue.mark_as_processed(messages)
            number_of_handled_messages += len(messages)
            print(f'invalidation queue messages handled so far: {number_of_handled_messages}')


if __name__ == '__main__':
    time.sleep(60)
    poll()
