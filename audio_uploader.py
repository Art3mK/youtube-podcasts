import youtube_dl
import glob
import boto3
import os

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
