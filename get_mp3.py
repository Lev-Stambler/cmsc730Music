#!/usr/bin/env python3

import subprocess
from time import sleep
from pytube import YouTube
import pytube
import os

yt_download_name = "YTDownload"
def get_mp3(video_url: str, trim_start: int, trim_end: int):
    # video_url = input('Enter YouTube video URL: ')

    path = os.getcwd() + '/'

    # name = pytube.extract.video_id(video_url)
    YouTube(video_url).streams.filter(only_audio=True).first().download(filename=yt_download_name + ".mp4")
    location = path + yt_download_name + '.mp4'
    renametomp3 = path + yt_download_name + '.mp3'

    os.system('mv {0} {1}'. format(location, renametomp3))
    sleep(1)
    # cmd = f"sox {yt_download_name}.mp3 {yt_download_name}.trim.mp3 trim {trim_start} -{trim_end}"
    cmd = f"ffmpeg -ss {trim_start} -t {trim_end - trim_start} -i {yt_download_name}.mp3 {yt_download_name}.trim.mp3 -y"
    print("CMD: ", cmd)
    os.system(cmd)
    sleep(1)
    # os.system(f'mv {yt_download_name}.trim.mp3 {yt_download_name}.mp3')