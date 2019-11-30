# -*- coding: utf-8 -*-

import os
import sys
import json
import boto3
import re
from feedgen.feed import FeedGenerator
from datetime import date, datetime, timedelta

def generate_feed(bucket, prefix, events, s3_client):
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.podcast.itunes_category('Podcasting')
    fg.id(f'https://podcasts.awsome.click/{prefix}')
    fg.title(f'Artem Kajalainen\'s feed for youtube\'s {prefix}')
    fg.author( {'name':'Artem Kajalainen','email':'artem@kayalaynen.ru'} )
    fg.link(href=f'http://podcasts.awsome.click/{prefix}/atom.xml', rel='self' )
    fg.language('ru')
    for event in events:
        entry = fg.add_entry()
        entry.id(event['id'])
        entry.title(event["title"])
        entry.summary(event["description"])
        entry.link(href=event["media"])
        entry.enclosure(event["media"], 0, "audio/m4a")
    fg.atom_file('atom.xml')
    s3_client.upload_file('atom.xml', bucket, f'{prefix}atom.xml', ExtraArgs={'ACL':'public-read', 'ContentType': "text/xml"})

def list_episodes(bucket, prefix, s3_client):
    episodes = []
    paginator = s3_client.get_paginator("list_objects")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys += [obj['Key'] for obj in page.get('Contents', []) if re.match(r'.*info.json', obj['Key'], flags=re.IGNORECASE)]
    for key in keys:
        episode_obj = s3_client.get_object(Bucket=bucket, Key=key)
        episode = json.loads(episode_obj['Body'].read())
        event = {}
        event['title'] = episode['title']
        event['description'] = episode['description']
        event['id'] = episode['id']
        event['media'] = f"http://{bucket}/{prefix}{episode['_filename']}"
        episodes.append(event)
    generate_feed(bucket, prefix, episodes, s3_client)

def main():
    S3_BUCKET = os.environ.get('S3_BUCKET')
    if S3_BUCKET is None:
        print("S3_BUCKET is not found in env")
        return 1
    # s3 = boto3.client('s3',endpoint_url='http://localhost:4572',aws_access_key_id="abc",aws_secret_access_key="bce")
    s3 = boto3.client('s3')

    paginator = s3.get_paginator("list_objects")
    for page in paginator.paginate(Bucket=S3_BUCKET,Delimiter="/"):
        for prefix in page.get('CommonPrefixes'):
            list_episodes(S3_BUCKET, prefix.get('Prefix'), s3)
    return 0

def lambda_handler(event, context):
    main()

if __name__ == "__main__":
    main()
