import requests
import time

from opensearchpy import OpenSearch

from snovault.queue import SQSQueueRepository
from snovault.queue import SQSQueueRepositoryProps
from snovault.queue import client
from snovault.queue import QUEUE_URL


auth = ('foobar', 'bazqux')
url = 'http://nginx:8000'
OPENSEARCH_URL = 'http://opensearch:9200'
opensearch_client = OpenSearch(
    OPENSEARCH_URL
)


def get_item(uuid):
    return requests.get(
        f'{url}/{uuid}/@@index-data-external/?datastore=database',
        auth=auth
    ).json()


def index_item(item):
    opensearch_client.index(
        index=item['item_type'],
        body=item,
        id=item['uuid'],
        request_timeout=30
    )


def get_uuids_from_transaction(message):
    uuids = set()
    payload = message.json_body['data']['payload']
    uuids.update(payload['updated'])
    uuids.update(payload['renamed'])
    return list(uuids)


def handle_messages(messages):
    for message in messages:
        uuids = get_uuids_from_transaction(message)
        for uuid in uuids:
            item = get_item(uuid)
            index_item(item)


def get_transaction_queue():
    transaction_queue = SQSQueueRepository(
        props=SQSQueueRepositoryProps(
            client=client,
            queue_url=QUEUE_URL,
        )
    )
    transaction_queue.wait_for_queue_to_exist()
    return transaction_queue


def poll():
    number_of_handled_messages = 0
    transaction_queue = get_transaction_queue()
    print('LISTENING to transaction queue')
    while True:
        messages = list(
            transaction_queue.get_messages(
                desired_number_of_messages=10
            )
        )
        if messages:
            handle_messages(messages)
            transaction_queue.mark_as_processed(messages)
            number_of_handled_messages += len(messages)
            print(f'transaction queue messages handled so far: {number_of_handled_messages}')


if __name__ == '__main__':
    time.sleep(20)
    poll()
