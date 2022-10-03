import logging
import os
import requests
import time

from opensearchpy import OpenSearch

from snovault.remote.queue import SQSQueue
from snovault.remote.queue import SQSQueueProps
from snovault.remote.queue import get_sqs_client


INVALIDATION_QUEUE_URL = os.environ['INVALIDATION_QUEUE_URL']

BACKEND_URL = os.environ['BACKEND_URL']

BACKEND_KEY = os.environ['BACKEND_KEY']

BACKEND_SECRET_KEY = os.environ['BACKEND_SECRET_KEY']

AUTH = (BACKEND_KEY, BACKEND_SECRET_KEY)

OPENSEARCH_URL = os.environ['OPENSEARCH_URL']

opensearch_client = OpenSearch(
    OPENSEARCH_URL
)

sqs_client = get_sqs_client()


def get_item(uuid):
    return requests.get(
        f'{BACKEND_URL}/{uuid}/@@index-data-external/?datastore=database',
        auth=AUTH
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
        index_item(item, version)


def get_invalidation_queue():
    invalidation_queue = SQSQueue(
        props=SQSQueueProps(
            client=sqs_client,
            queue_url=INVALIDATION_QUEUE_URL,
        )
    )
    invalidation_queue.wait_for_queue_to_exist()
    return invalidation_queue


def wait_for_access_key_to_exist():
    logging.warning('Checking for access key')
    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(
                f'{BACKEND_URL}/access-keys/?datastore=database',
                auth=AUTH
            )
        except requests.exceptions.ConnectionError:
            time.sleep(attempt * 5)
            continue
        if response.status_code == 200:
            logging.warning(f'Found access key, attempt {attempt}')
            break
        time.sleep(attempt * 3)


def poll():
    number_of_handled_messages = 0
    invalidation_queue = get_invalidation_queue()
    print('LISTENING to invalidation queue')
    wait_for_access_key_to_exist()
    while True:
        messages = list(
            invalidation_queue.get_messages(
                desired_number_of_messages=1
            )
        )
        if messages:
            handle_messages(messages)
            invalidation_queue.mark_as_processed(messages)
            number_of_handled_messages += len(messages)
            if number_of_handled_messages % 100 == 0:
                print(f'invalidation queue messages handled so far: {number_of_handled_messages}')


if __name__ == '__main__':
    poll()
