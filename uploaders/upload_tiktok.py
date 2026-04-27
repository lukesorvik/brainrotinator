
from tiktok_uploader.upload import upload_video, upload_videos
from tiktok_uploader.auth import AuthBackend


#https://github.com/wkaisertexas/tiktok-uploader?tab=readme-ov-file
def upload_video_Tiktok(video_path :str, description:str, cookies:str) -> None:

    username = 'your username here'
    password = 'password here'

    upload_video(filename=video_path, description=description, cookies= cookies, username=username, password=password)




