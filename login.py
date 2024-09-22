import os
from youtube_uploader_selenium import YouTubeUploader
from Instagram_Uploader.instagramUploader import InstagramUploader
from termcolor import colored

def login_youtube(metadata:str) -> None:
    print(colored("Logging in to Youtube", "blue"))
    uploader = YouTubeUploader("dummy", metadata, headless= False)
    uploader.login()
    
def login_instagram(metadata:str) -> None:
    print(colored("Logging in to Instagram", "magenta"))
    uploader = InstagramUploader("dummy",metadata, headless= False)
    uploader.login()
    
if __name__ == "__main__":
    print(colored("Logging in to Youtube and Instagram to save cookies for future use", "green"))
    print(colored("Firefox browser required", "yellow"))
    outputDirectory :str = os.path.join(os.getcwd(), "done_split")
    metadata_path :str = os.path.join(outputDirectory, "upload.json")
    login_youtube(metadata_path)
    login_instagram(metadata_path)
    print(colored("Cookies saved successfully. Now you can upload videos without logging in again", "cyan"))
