# -*- coding: utf-8 -*-

import os
import sys
import json
import boto3

SQS_QUEUE_URL = None

def post_sqs_message(message_body):
    global SQS_QUEUE_URL
    sqs = boto3.client('sqs')

    response =  sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=message_body
    )
    print(response['MessageId'])

def main():
    global SQS_QUEUE_URL
    SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
    if SQS_QUEUE_URL is None:
        print("SQS_QUEUE_URL is not found in env")
        return 1
    S3_BUCKET = os.environ.get('S3_BUCKET')
    if S3_BUCKET is None:
        print("S3_BUCKET is not found in env")
        return 1
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=S3_BUCKET, Key='sources.json')
    sources = json.loads(obj['Body'].read())
    print(sources)
    for channel in sources['channels']:
        post_sqs_message(json.dumps({'type': 'channel', 'id': channel['id']}))
    for playlist in sources['playlists']:
        post_sqs_message(json.dumps({'type': 'playlist', 'id': playlist['id']}))
    return 0

if __name__ == "__main__":
    sys.exit(main())

def lambda_handler(event, context):
    main()
