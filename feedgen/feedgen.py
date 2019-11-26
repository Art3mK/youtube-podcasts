# -*- coding: utf-8 -*-

import os
import sys
import json
import boto3
from datetime import date, datetime, timedelta

def generate_feed(bucket, prefix):
    pass

def main():
    S3_BUCKET = os.environ.get('S3_BUCKET')
    if S3_BUCKET is None:
        print("S3_BUCKET is not found in env")
        return 1
    s3 = boto3.client('s3')

    paginator = s3.get_paginator("list_objects")
    for page in paginator.paginate(Bucket=S3_BUCKET,Delimiter="/"):
        for prefix in page.get('CommonPrefixes'):
            generate_feed(S3_BUCKET, prefix.get('Prefix'))
    return 0
def fetch_channel_videos(channel_id, youtube_client, published_after=None):
    request = youtube_client.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=50,
        order="date",
        type="video",
        publishedAfter=published_after
    )

    entries = []

    while request is not None:
        data = request.execute()
        if len(data['items']) > 0:
            entries += data['items']
        # fetch only last 50 videos for channel
        if len(entries) >= 50: break
        request = youtube_client.search().list_next(request, data)

    for item in entries:
        # push each video id to SQS
        body = json.dumps(
            {
            'videoId':item['id']['videoId'],
            'title': item['snippet']['title'],
            'channel_title': item['snippet']['channelTitle'],
            'publishedDate': item['snippet']['publishedAt']
            },
            ensure_ascii=False
        )
        print(body)
        if not check_dynamodb_record_exists(item['id']['videoId']):
            add_dynamodb_record(item['id']['videoId'])
            post_sqs_message(body)
        else:
            print('record already exists')
    return 0

def fetch_playlist_videos(playlist_id, youtube_client):
    request = youtube_client.playlists().list(
        part="snippet",
        id=playlist_id
    )

    data = request.execute()

    playlist_title = data['items'][0]['snippet']['title']

    request = youtube_client.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )

    response = request.execute()

    entries = []

    while request is not None:
        data = request.execute()
        if len(data['items']) > 0:
            entries += data['items']
        request = youtube_client.playlistItems().list_next(request, data)

    for item in entries:
        # push each video id to SQS
        snippet = item['snippet']
        if snippet['resourceId']['kind'] == 'youtube#video':
            body = json.dumps(
                {
                'videoId':snippet['resourceId']['videoId'],
                'title': item['snippet']['title'],
                'channel_title': playlist_title,
                'publishedDate': item['snippet']['publishedAt']
                },
                ensure_ascii=False
            )

        print(body)
        if not check_dynamodb_record_exists(snippet['resourceId']['videoId']):
            add_dynamodb_record(snippet['resourceId']['videoId'], expire=False)
            post_sqs_message(body)
        else:
            print('record already exists')
    return 0

def lambda_handler(event, context):



    YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
    if YT_API_KEY is None:
        print("YOUTUBE_API_KEY is not found in env")
        return 1
    if SQS_QUEUE_URL is None:
        print("SQS_QUEUE_URL is not found in env")
        return 1
    api_service_name = "youtube"
    api_version = "v3"
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=YT_API_KEY, cache_discovery=False)

    for record in event['Records']:
        data = json.loads(record['body'])
        if data['type'] == 'channel':
            # get 3 months old videos only
            three_months_ago = (datetime.utcnow() - timedelta(days=90)).isoformat("T") + "Z"
            fetch_channel_videos(data['id'], youtube, three_months_ago)
        elif data['type'] == 'playlist':
            fetch_playlist_videos(data['id'], youtube)
        else:
            print("Does not compute")
            print(record)

if __name__ == "__main__":
    main()
