import youtube_dl
import glob
import boto3
import os
import json

ydl_opts = {
    'format': 'bestaudio[ext=m4a]',
    'outtmpl': '/tmp/%(title)s.%(ext)s'
}

def download_audio_file(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def upload_to_s3(folder, bucket):
    for file in glob.glob("/tmp/*.m4a"):
        file_name = os.path.basename(file)
        s3 = boto3.client('s3')
        print(f"Uploading {folder}/{file_name} to s3://{bucket}")
        s3.upload_file(file, bucket, f'{folder}/{file_name}', ExtraArgs={'ACL':'public-read', 'ContentType': "audio/m4a"})

if __name__ == "__main__":
    download_audio_file('https://www.youtube.com/watch?v=1wYLsMmwZkM')
    upload_to_s3('buff_dudes','podcasts.awsome.click')

def lambda_handler(event, context):
    S3_BUCKET = os.environ.get('S3_OUTPUT_BUCKET')
    if S3_BUCKET is None:
        print("S3_OUTPUT_BUCKET is not found in env")
        return 1
    for record in event['Records']:
        data = json.loads(record['body'])
        print(data)
        download_audio_file(data['videoId'])
        upload_to_s3(data['channel_title'], S3_BUCKET)
    # {
    #     "Records": [
    #         {
    #             "messageId": "2c43e23b-fc9f-40fc-b1d7-8f822e78f47e",
    #             "receiptHandle": "AQEBWpE6IekW0VYM3Z9LK1RIU9yWRVMatSQlEenijy4rQUiW/eU1nZ6yh5rXc5W985RbQsUGdbU2AwqPge6A5JvgdwYu5CS3m8TiAVQpLnVyF8YKL6XtAl2k0X1PfhBVOs8CIPrGwbb9aZPNuvKk5wXy5M/lBF2ZMKL6y8LUEoTHIuxxzXO+tokHJ4dBjp1AM5q2EsKDhGHtg1wbatydo+eUQvdjuRSAtpqt4cqHUwRQKi5u1RGloDk/47zJJntW28i0JxmrJabxonaKRzrEtX7whOqegy+DBfEoW2+C30Q5TH466tmLpry9MB8DotZOC1pOHZw6C7mi8gLF3BJxXU9NhSbPazMLmHAnJXfInKMm1eINPzIWQmdtxDwk8gLpCvZUxTazcD6Lzmg3X5qDoC2LIw==",
    #             "body": {
    #                 "videoId": "1wYLsMmwZkM",
    #                 "title": "Best Gym Exercises You&#39;re Not Doing!",
    #                 "channel_title": "Buff Dudes"
    #             },
    #             "attributes": {
    #                 "ApproximateReceiveCount": "1",
    #                 "SentTimestamp": "1571814427016",
    #                 "SenderId": "AIDAJV7JQQLG32TOS7BYM",
    #                 "ApproximateFirstReceiveTimestamp": "1572009070850"
    #             },
    #             "messageAttributes": {},
    #             "md5OfBody": "3221d21455b5e20b9a2cb77f12ab5169",
    #             "eventSource": "aws:sqs",
    #             "eventSourceARN": "arn:aws:sqs:eu-north-1:1234567890:youtube-podcasts",
    #             "awsRegion": "eu-north-1"
    #         }
    #     ]
    # }