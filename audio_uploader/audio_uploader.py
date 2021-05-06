import youtube_dl
from youtube_dl import DownloadError
import glob
import boto3
import os
import traceback
import logging
import json

ydl_opts = {
    'format': 'bestaudio',
    'outtmpl': '/tmp/%(title)s.%(ext)s',
    'writeinfojson': True,
    'cachedir': False
}

def download_audio_file(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return 0
        except DownloadError as down_error:
            print(f"Can't download {url}")
            print(down_error)
            return 1
        except Exception as e:
            logging.error(traceback.format_exc())
            return 1

def upload_to_s3(folder, bucket):
    # s3 = boto3.client('s3',endpoint_url='http://localhost:4572',aws_access_key_id="abc",aws_secret_access_key="bce")
    s3 = boto3.client('s3')
    for file in glob.glob("/tmp/*.info.json"):
        file_name = os.path.basename(file)
        info_file = open(file, "r")
        video_file = json.loads(info_file.read())['_filename']
        info_file.close()
        print(f"Uploading {folder}/{file_name} to s3://{bucket}")
        s3.upload_file(file, bucket, f'{folder}/{file_name}', ExtraArgs={'ACL': 'public-read', 'ContentType': "text/json"})
        print(f"Uploading {folder}/{os.path.basename(video_file)} to s3://{bucket}")
        s3.upload_file(video_file, bucket, f'{folder}/{os.path.basename(video_file)}', ExtraArgs={'ACL': 'public-read'})
        # lambdas are reused, so clean up /tmp
        os.remove(file)
        os.remove(video_file)


def clean_ddb(video_id):
    print(f"I'm gonna remove video id: {video_id} from DDB")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('videos')
    table.delete_item(
        Key={
            'video_id': video_id
        }
    )


if __name__ == "__main__":
    download_audio_file('https://www.youtube.com/watch?v=Lqe54ihSkUY')
    # download_audio_file('https://www.youtube.com/watch?v=dqwpQarrDwk')
    # download_audio_file('https://www.youtube.com/watch?v=udFxKZRyQt4')
    # upload_to_s3('buff_dudes','podcasts.awsome.click')

def lambda_handler(event, context):
    S3_BUCKET = os.environ.get('S3_OUTPUT_BUCKET')
    if S3_BUCKET is None:
        print("S3_OUTPUT_BUCKET is not found in env")
        return 1
    # event from state machine state
    # {
    #     "videoId": "a3713oGB6Zk",
    #     "title": "AWS re:Invent 2017: Big Data Architectural Patterns and Best Practices on AWS (ABD201)",
    #     "channel_title": "челпанова",
    #     "publishedDate": "2020-08-12T13:35:26Z"
    # }
    print(event)
    if download_audio_file(event['videoId']) == 0:
        upload_to_s3(event['channel_title'], S3_BUCKET)
    else:
        clean_ddb(event['videoId'])
