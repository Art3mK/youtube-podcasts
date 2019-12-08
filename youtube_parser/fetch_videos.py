# -*- coding: utf-8 -*-

import os
import sys
import json
import boto3
import urllib.request
import re
from datetime import date, datetime, timedelta

import googleapiclient.discovery
import googleapiclient.errors

SQS_QUEUE_URL = None
S3_BUCKET = None

def upload_channel_thumbnail(channel_title, thumbnail_url):
    global S3_BUCKET
    s3 = boto3.client('s3')
    urllib.request.urlretrieve(thumbnail_url, '/tmp/thumbnail.jpg')
    s3.upload_file('/tmp/thumbnail.jpg', S3_BUCKET, f'{channel_title}/thumbnail.jpg', ExtraArgs={'ACL':'public-read', 'ContentType': "image/jpg"})
    os.remove('/tmp/thumbnail.jpg')

def post_sqs_message(message_body):
    global SQS_QUEUE_URL
    sqs = boto3.client('sqs')

    response =  sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=message_body
    )
    print(response['MessageId'])

def fetch_channel_videos(channel_id, youtube_client, published_after=None):
    # fetch thumbnail for channel and upload it to s3
    request = youtube_client.channels().list(
        part="snippet",
        id=channel_id
    )

    response = request.execute()
    channel_thumbnail = response['items'][0]['snippet']['thumbnails']['high']['url']

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

    upload_thumbnail = True
    posted_items = 0
    for item in entries:
        channel_title = re.sub('["@\']','',item['snippet']['channelTitle'])
        if upload_thumbnail:
            upload_thumbnail = False
            upload_channel_thumbnail(channel_title, channel_thumbnail)
        # push each video id to SQS
        body = json.dumps(
            {
            'videoId':item['id']['videoId'],
            'title': item['snippet']['title'],
            'channel_title': channel_title,
            'publishedDate': item['snippet']['publishedAt']
            },
            ensure_ascii=False
        )
        print(body)
        if not check_dynamodb_record_exists(item['id']['videoId']):
            add_dynamodb_record(item['id']['videoId'], item['snippet']['title'], channel_title)
            post_sqs_message(body)
            posted_items += 1
        else:
            print('record already exists')
    update_video_counter(posted_items)
    return 0

def fetch_playlist_videos(playlist_id, youtube_client):
    request = youtube_client.playlists().list(
        part="snippet",
        id=playlist_id
    )

    data = request.execute()

    playlist_title = re.sub('["@\']','',data['items'][0]['snippet']['title'])
    playlist_thumbnail = data['items'][0]['snippet']['thumbnails']['high']['url']

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

    upload_thumbnail = True
    posted_items = 0
    for item in entries:
        if upload_thumbnail:
            upload_thumbnail = False
            upload_channel_thumbnail(playlist_title, playlist_thumbnail)
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
            add_dynamodb_record(snippet['resourceId']['videoId'], item['snippet']['title'], playlist_title, expire=False)
            post_sqs_message(body)
            posted_items += 1
        else:
            print('record already exists')
    update_video_counter(posted_items)
    return 0

def add_dynamodb_record(video_id, title, channel_title, expire=True):
    item = {
        'video_id': video_id,
        'title': title,
        'channel_title': channel_title
    }

    if expire:
        item['TTL'] = (date.today() + timedelta(days=90)).strftime("%s")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('videos')
    table.put_item(
        Item=item
    )

def check_dynamodb_record_exists(video_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('videos')
    response = table.get_item(
        Key={
             'video_id': video_id
        }
    )
    if 'Item' in response:
        item = response['Item']
        print(f'Found record in dynamodb: {item}')
        return True
    return False

def update_video_counter(counter):
    print(f"Updating DDB counter to {counter}")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('videos_counter')
    response = table.update_item(
        Key={ 'id': 'audio_uploader' },
        UpdateExpression="set queue = queue + :val",
        ExpressionAttributeValues={
            ':val': counter
        }
    )

def lambda_handler(event, context):
    global SQS_QUEUE_URL
    global S3_BUCKET
    YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
    S3_BUCKET = os.environ.get('S3_BUCKET')
    if YT_API_KEY is None:
        print("YOUTUBE_API_KEY is not found in env")
        return 1
    if SQS_QUEUE_URL is None:
        print("SQS_QUEUE_URL is not found in env")
        return 1
    if S3_BUCKET is None:
        print("S3_BUCKET is not found in env")
        return 1

    api_service_name = "youtube"
    api_version = "v3"
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=YT_API_KEY, cache_discovery=False)

    for record in event['Records']:
        data = json.loads(record['body'])
        if data['type'] == 'channel':
            # get 3 months old videos only
            three_months_ago = (datetime.utcnow() - timedelta(days=90)).isoformat("T") + "Z"
            # fetch_channel_videos(data['id'], youtube, three_months_ago)
            fetch_channel_videos(data['id'], youtube)
        elif data['type'] == 'playlist':
            fetch_playlist_videos(data['id'], youtube)
        else:
            print("Does not compute")
            print(record)
