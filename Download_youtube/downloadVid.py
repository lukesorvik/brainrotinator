import sys
from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
from typing import Any, Callable, Dict, List, Optional
from termcolor import colored
from Download_youtube.combineAudioVideo import CombineAudioVideo

#uses pytube to download video from youtube


"""
Download a video from youtube
@param url: the url of the video
@param path: the path to download the video to
"""
def download_vid(url, path):
    
    yt = YouTube(url, on_progress_callback=on_progress)


    Streams = yt.streams
    print(colored(f"Streams: {Streams}", "blue"))

    # Get the video title
    video_title :str = str(yt.title)
    print(colored(f"Downloading video: {video_title}", "green"))
    #trunckate video title to 10 character, no special characters
    video_title = video_title[:100].replace(" ", "_").replace(":", "_").replace("|", "_").replace("?", "_").replace("/", "_").replace("\\", "_").replace("*", "_").replace("<", "_").replace(">", "_").replace("\"", "_").replace(";", "_").replace(",", "_").replace("!", "_").replace(".", "_")

    print("Order of streams highest res: "+ str(yt.streams.filter(file_extension='mp4', only_video=True).order_by('resolution').desc()))
    video_stream  = yt.streams.filter(file_extension='mp4', only_video=True).order_by('resolution').desc().first()  
    #order by resolution, get the highest resolution, should be the first one
    print(colored(f"Downloading video stream: {video_stream}", "green"))

    # Get the highest quality audio stream
    audio_stream = Streams.get_audio_only()
    print(colored(f"Downloading audio stream: {audio_stream}", "green"))

    videoFolder = os.path.join(path, "video")
    audioFolder = os.path.join(path, "audio")

    # Download the streams
    filename = video_title + ".mp4"
    video_stream.download(videoFolder, filename)
    audio_stream.download(audioFolder, filename)

    videoName = os.path.join(videoFolder, video_title + ".mp4")
    audioName = os.path.join(audioFolder, video_title + ".mp4")


    print(colored(f"Video downloaded to: {videoName}", "green"))
    print(colored(f"Audio downloaded to: {audioName}", "green"))
    
    #now call to combine
    CombineAudioVideo(videoName,audioName, path, filename)
    


#main function for when this is run as a standalone script
def main():
    #first two args are url for video and path to download to
    #display help if not enough args
    if len(sys.argv) < 3:
        print("Usage: python downloadVid.py <url> <path>")
        sys.exit(1)
    
    path = sys.argv[2]
    url = sys.argv[1]
    

    print("URL: " + url)
    print("Path: " + path)

    download_vid(url, path)


if __name__ == "__main__":
    main()