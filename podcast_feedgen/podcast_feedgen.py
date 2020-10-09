# -*- coding: utf-8 -*-

import json
import os
import re
import boto3
import urllib.parse
from feedgen.feed import FeedGenerator

def generate_feed(bucket, prefix, events, s3_client):
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.podcast.itunes_category('Podcasting')
    fg.podcast.itunes_image(f'http://podcasts.awsome.click/{prefix}thumbnail.jpg')
    fg.id(f'http://podcasts.awsome.click/{prefix}')
    fg.title(f'Artem Kajalainen\'s feed for youtube\'s {prefix}')
    fg.author( {'name':'Artem Kajalainen','email':'artem@kayalaynen.ru'} )
    fg.link(href=f'http://podcasts.awsome.click/{prefix}/atom.xml', rel='self' )
    fg.description('youtube videos as podcast')
    fg.language('ru')
    for event in events:
        entry = fg.add_entry()
        entry.id(event['id'])
        entry.title(event["title"])
        entry.summary(event["description"])
        entry.link(href=event["media"])
        entry.enclosure(event["media"], 0, "audio/m4a")
        entry.podcast.itunes_image(event['thumbnail'])
    fg.rss_file('/tmp/feed.rss')
    s3_client.upload_file('/tmp/feed.rss', bucket, f'{prefix}feed.rss', ExtraArgs={'ACL':'public-read', 'ContentType': "text/xml"})
    os.remove('/tmp/feed.rss')

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
        event['media'] = f"https://s3.eu-north-1.amazonaws.com/podcasts.awsome.click/" + urllib.parse.quote_plus(f"{prefix}{os.path.basename(episode['_filename'])}",safe="/")
        event['thumbnail'] = f"https://img.youtube.com/vi/{event['id']}/sddefault.jpg"
        print(event)
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
            print(f"Doing stuff on prefix {prefix.get('Prefix')}")
            list_episodes(S3_BUCKET, prefix.get('Prefix'), s3)
    return 0

def lambda_handler(event, context):
    main()

if __name__ == "__main__":
    main()
