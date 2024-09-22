from youtube_uploader_selenium import YouTubeUploader
#from https://github.com/linouk23/youtube_uploader_selenium
from Instagram_Uploader.instagramUploader import InstagramUploader

def upload_video_youtube(video_path: str, metadata_path: str, headless: bool, i : int = 0) -> None:
    uploader = YouTubeUploader(video_path, metadata_path, headless=headless)
    try:
      uploader.upload() 
    except Exception as e:
      print(f"Error uploading video: {e}")
      print("Retrying upload...")
      if i < 5:
        print(f"Retry number {i}")
        i += 1
        upload_video_youtube(video_path, metadata_path, headless, i) # retry the upload recursively
    

def upload_video_Instagram(video_path: str, metadata_path: str, headless: bool, i: int = 0) -> None:
    uploader = InstagramUploader(video_path, metadata_path, headless=headless)
    try:
      uploader.upload()
    except Exception as e:
      print(f"Error uploading video: {e}")
      print("Retrying upload...")
      
      if(i < 5):
        print(f"Retry number {i}")
        i += 1
        upload_video_Instagram(video_path, metadata_path,headless, i) # retry the upload recursively
    

