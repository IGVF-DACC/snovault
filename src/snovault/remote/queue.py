import boto3
import os


def get_sqs_client():
    localstack_endpoint_url = os.environ.get(
        'LOCALSTACK_ENDPOINT_URL'
    )
    if localstack_endpoint_url:
        return boto3.client(
            'sqs',
            endpoint_url=localstack_endpoint_url,
            aws_access_key_id='testing',
            aws_secret_access_key='testing',
            region_name='us-west-2',
        )
    return boto3.client(
        'sqs'
    )
