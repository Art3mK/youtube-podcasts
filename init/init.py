# -*- coding: utf-8 -*-

import os
import sys
import json
import boto3

def main():
    S3_BUCKET = os.environ.get('S3_BUCKET')
    if S3_BUCKET is None:
        print("S3_BUCKET is not found in env")
        sys.exit(1)
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=S3_BUCKET, Key='sources.json')
    sources = json.loads(obj['Body'].read())
    print(sources)
    data = []
    for channel in sources['channels']:
        data.append({'type': 'channel', 'id': channel['id']})
    for playlist in sources['playlists']:
        data.append({'type': 'playlist', 'id': playlist['id']})
    return data

if __name__ == "__main__":
    main()

def lambda_handler(event, context):
    return(main())
