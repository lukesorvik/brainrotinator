from datetime import datetime, timedelta
import platform
from video_editor import VideoEditor
import os
import time
import argparse
import random
from typing import Dict, Any
import shutil
from uploader_selenium import upload_video_youtube, upload_video_Instagram
import json
from Download_youtube.downloadVid import download_vid
import subprocess
from subprocess import Popen, PIPE
import sys
from upload_tiktok import upload_video_Tiktok

class Color:
                PURPLE = '\033[95m'
                CYAN = '\033[96m'
                DARKCYAN = '\033[36m'
                BLUE = '\033[94m'
                GREEN = '\033[92m'
                YELLOW = '\033[93m'
                RED = '\033[91m'
                BOLD = '\033[1m'
                UNDERLINE = '\033[4m'
                END = '\033[0m'
                
                

"""
Function to upload the chunks to YouTube
Uploads videos from the done_split folder, uploads until reaches howManyUploads, then sleeps for 23 hours

time between uploads = howManyMinsBetweenUpload + random wait of 0-5 mins

@param output_directory - path to the output directory(folder with the clips of our videos)
@param howManyUploads - how many times to upload before sleeping for 24 hours
@param howManyHoursBetweenUpload - how many hours delay between each upload scheduled to be uploaded
@param howManyMinsBetweenUpload - how many minutes to wait between each upload
@param howManyHoursLongToSleep - how many hours to sleep after uploading howManyUploads times
@param tags - list of tags to add to the video
@param description_video - description of the video

"""
def uploadVideos(doneVideosDirectory : str, 
            howManyUploads : int, 
            howManyHoursBetweenSchedule : int,
              howManyMinsBetweenUpload:int, 
              howManyHoursLongToSleep:int,
           tags: list[str],
           description_video: str
           ) -> None:
    print(Color.GREEN + "Done Videos directory: " + doneVideosDirectory + Color.END)
    print(Color.BLUE + "Video Upload Order order: \n" + str(os.listdir(doneVideosDirectory)) + "\n\n" + Color.END)

    i : int = 0
    for videoFileName in os.listdir(doneVideosDirectory):
        print(Color.BLUE+ "Video file: " + videoFileName + Color.END)
        
        if videoFileName.endswith(".mp4"):
            print(Color.GREEN + f"i = {i} \n"  + videoFileName + Color.END)

            #if we have uploaded howmanyUploads times and is not first upload since starting program, sleep for howManyHoursLongToSleep 
            if(i % howManyUploads == 0 and i != 0) :
                timeToSleepInHours =  (howManyHoursLongToSleep*60*60)
                print(Color.GREEN + f"Sleeping for {howManyHoursLongToSleep} hrs since uploaded {howManyUploads} vids... \n calculated: {timeToSleepInHours/60/60} hrs " + Color.END)
                
                nextUploadTime = datetime.now() + timedelta(seconds=timeToSleepInHours)
                print(Color.BLUE+ f" => next upload at {nextUploadTime}" + Color.END)

                #Sleep for howManyHoursLongToSleep hours 
                time.sleep(timeToSleepInHours)
                i = 0 #reset the counter to 0 after sleeping for 24 hours

            #if we are not on the first video, sleep for hour since we have uploaded a video
            if(i != 0) : 
                print(Color.GREEN + "Time now: " + str(datetime.now()) + Color.END)


                randomSleepSeconds = random.randint(0, 300)
                sleepTimeSeconds = (howManyMinsBetweenUpload * 60) + randomSleepSeconds 
               
                now = datetime.now()
                nextUploadTime = now + timedelta(seconds=sleepTimeSeconds)

                print(Color.BLUE+ f" => next upload at {nextUploadTime}" + Color.END)
                print(Color.GREEN + "Sleeping for:"+str(sleepTimeSeconds /60) + "minutes" + Color.END)
                time.sleep(sleepTimeSeconds) #sleep for 1 hour before uploading the next video
            

            print(Color.GREEN+ "\n ---------------------------------------------------------------------" + Color.END)
            if uploadToYoutube:
                print(Color.GREEN+ "Uploading video to YouTube..." + Color.END)

            videoFilePath :str = os.path.join(doneVideosDirectory, videoFileName)
            print(Color.GREEN+"Uploading video from: \n" + videoFilePath + Color.END)

            videoFileNameWithoutMP4ForSummary :str = os.path.splitext(videoFileName)[0]  
            print(Color.GREEN + "Base name: " + videoFileNameWithoutMP4ForSummary + Color.END)

            #if "_filtered" in videoFileNameWithoutMP4: remove the "_filtered" from the name
            #ai summary file is named without the "_filtered" so we need to remove it from the name
            if "_filtered" in videoFileNameWithoutMP4ForSummary:
                videoFileNameWithoutMP4ForSummary = videoFileNameWithoutMP4ForSummary.replace("_filtered", "")
                print(Color.GREEN + "Base name after removing '_filtered': " + videoFileNameWithoutMP4ForSummary + Color.END)

            project_root :str  = os.getcwd()
            subtitles_path :str = os.path.join(project_root, "subtitles")
            print(Color.YELLOW + "Subtitles path: " + subtitles_path + Color.END)

            AISummaryPath: str = os.path.join(subtitles_path, f"{videoFileNameWithoutMP4ForSummary}_summary.txt")

            print(Color.YELLOW + "Summary path: " + AISummaryPath + Color.END)

            AiTitle :str  = ""
            
            try:
                with open(AISummaryPath, "r") as f:
                    AiTitle = f.read()
            except FileNotFoundError:
                print(Color.RED + "Summary file not found: " + AISummaryPath + Color.END)
                AiTitle = "default"  
            
            print(Color.YELLOW + "Ai Title: " + AiTitle + Color.END)
            print(Color.BLUE+ f" => Scheduling video to be uploaded in {i * howManyHoursBetweenSchedule} hours" + Color.END)

            # Calculate the scheduled time based on the number of iterations
            now = datetime.now() 
            random_mins = random.randint(0, 10) 
            howManyHoursLaterToSchedule = now + timedelta(hours=(i * howManyHoursBetweenSchedule), minutes=random_mins) #hr+rand mins to avoid getting banned

            # Format the time in ISO 8601 format
            formatted_time = howManyHoursLaterToSchedule.strftime("%m/%d/%Y, %H:%M")
            print("Current time:", now)
            print(f"{i*howManyHoursBetweenSchedule} hours later:", howManyHoursLaterToSchedule)
            print("ISO format:", formatted_time)

            #initialize the json object
            upload_json = {} 
            
            #if we are on the first video, upload immediately or if we are not scheduling the video
            if (i == 0 or howManyHoursBetweenSchedule == 0): 
                print(Color.GREEN + "Uploading immediately..." + Color.END)
                upload_json = {
                    "title": AiTitle,
                    "description": description_video,
                    "tags": tags,
                }

            #if we are not on the first video, schedule the video to be uploaded in future
            else : 
                print(Color.GREEN + "Scheduling video to be uploaded in the future..." + Color.END)
                upload_json = {
                    "title": AiTitle,
                    "description": description_video,
                    "tags": tags,
                    "schedule": formatted_time
                }

            json_file_path :str = os.path.join(doneVideosDirectory, "upload.json")
            with open(json_file_path, "w") as json_file:
                json.dump(upload_json, json_file)
            print(Color.GREEN + "JSON file path: " + json_file_path + Color.END)

            if uploadToYoutube:
                upload_video_youtube(videoFilePath, json_file_path, headless = firefoxHeadless) 
                print(Color.GREEN+ "Uploaded video to youtube: " + videoFileName + Color.END)

            print(Color.GREEN+ "\n ---------------------------------------------------------------------" + Color.END)

            copyOfTags = tags.copy() #copy the tags so we dont modify the original list

            for x in range(len(copyOfTags)):
                copyOfTags[x] = "#" + copyOfTags[x].replace(" ", "") 
                
            AiTitle = AiTitle + " " + " ".join(copyOfTags)

            print(Color.GREEN + "Title for TikTok+Instagram: " + AiTitle + Color.END)
            
            upload_json = {
                    "title": AiTitle,
                    "description": AiTitle,
                }
            with open(json_file_path, "w") as json_file:
                json.dump(upload_json, json_file)
                
            if uploadToInstagram:
                print(Color.GREEN+ "Uploading video to Instagram..." + Color.END)
                upload_video_Instagram(videoFilePath, json_file_path, headless = firefoxHeadless)
                print(Color.GREEN + "Uploaded to Instagram " + Color.END)

            print(Color.GREEN+ "\n ---------------------------------------------------------------------" + Color.END)
            

            cookies : str = os.path.join(project_root, "cookies-tiktok.txt")
            if uploadToTiktok:
                print(Color.GREEN + "Uploading to TikTok..." + Color.END)
                upload_video_Tiktok(video_path=videoFilePath, description= AiTitle, cookies = cookies)
                print(Color.GREEN + "Uploaded to TikTok " + Color.END)

            #-----------------------------------------------------------------------------

            move_files_to_uploaded(videoFileName, doneVideosDirectory, videoFilePath) #move the uploaded video to the uploaded folder

            i += 1 #increment the counter (only if we just uploaded a video, if not then dont increment hour time)


# Move the uploaded video to the "uploaded" directory, so we don't upload it again if the script crashes
def move_files_to_uploaded(videoFileName: str, doneVideoDirectory: str, videoFilePath) -> None:

            uploaded_directory = os.path.join(doneVideoDirectory, "uploaded")
            print(Color.GREEN + "Uploaded directory: " + uploaded_directory + Color.END)

            newVideoFilePath = os.path.join(uploaded_directory, videoFileName)
            shutil.move(videoFilePath, newVideoFilePath)
            print(Color.GREEN + f"Moved uploaded video to: {newVideoFilePath}" + Color.END)
            

        


"""
Function that goes through the to_split folder and splits each video into chunks
If no mp4 files in the folder, prompts user to add mp4 files to the folder, or exit editing
Only splits mp4 files
@param folder_path - the path to the folder with the video
@param output_directory - the path to the output folder
@param chunk_duration - the duration of each chunk in seconds
@param edited_directory - the path to the edited folder
@param gui - boolean to check if the program is running in GUI mode
@param splitOneVideo - boolean to check if the program is splitting one video
"""
def splitVideos(folder_path : str, 
                  output_directory : str, 
                  chunk_duration : int, 
                  edited_directory: str,
                  gui: bool = False,
                  splitOneVideo: bool = False) -> None:
    print(Color.GREEN+ "\n ---------------------------------------------------------------------" + Color.END)
    if(splitOneVideo):
        print(Color.GREEN + "Splitting one video..." + Color.END)
    else:
        print(Color.GREEN + "Splitting all videos in to_Split folder..." + Color.END)

    #for each video in the folder, split the video into 60 second chunks
    for video_file in os.listdir(folder_path):
        print(Color.BLUE + "Video file: " + video_file + Color.END )

        if video_file.endswith(".mp4"):
            input_video_path = os.path.join(folder_path, video_file)
            print("Input video path: " + input_video_path)

            base_name = os.path.splitext(video_file)[0]  # Get the base name without .mp4
            print(Color.GREEN + "Base name: " + base_name + Color.END)

            #initialize the class with (video_path, output_folder, chunk_duration, vname)
            video_editor = VideoEditor(input_path=input_video_path, 
                                       output_folder=output_directory, 
                                       chunk_duration=chunk_duration, 
                                       name= base_name, 
                                       useWhisper=useWhisperForTranscription,
                                       filterProfanityInSubtitles=filterProfanityInSubtitles,
                                       voskModelDir=voskModelDir,
                                       tinyLlamaDir=tinyLlamaDir)
            if blurred:
                print (Color.RED + "Split the video into chunks using blur" + Color.END)
                video_editor.split_video_into_chunks_blur() 
            else : 
                print (Color.RED + "Split the video into chunks without blur" + Color.END)
                video_editor.split_video_into_chunks()
            
            print (Color.GREEN + "Done editing the video into chunks" + Color.END)


            # Move the original video to the "edited" directory
            new_file_path = os.path.join(edited_directory, video_file)

            print("Input video path: " + input_video_path)
            print("New file path: " + new_file_path)

            while(True):
                try:
                    shutil.move(input_video_path, new_file_path)
                    print(Color.GREEN + f"Moved original video to: {new_file_path}" + Color.END)
                    break
                except Exception as e:
                    print(Color.RED + "Error moving file: " + str(e) + Color.END)
                    time.sleep(5)
            #if we are only splitting one video, break out of the loop
            if splitOneVideo:
                return
    
    #if reach here then no mp4 files in the folder (since would have broken out of the loop if there was a mp4 file)
    #prompt user to give url to download new youtube video
    if(gui):
        print("GUI mode")
        #return ui.promptUserToGiveVideoPath(folder_path, output_directory, chunk_duration, edited_directory)
        return
    else:
        print("CLI mode")
        return promptUserForURLCLI(folder_path, output_directory, chunk_duration, edited_directory)


def promptUserForURLCLI(folder_path : str, 
                        output_directory : str, 
                        chunk_duration : int, 
                        edited_directory: str) -> None:
    print(Color.RED + "No mp4 files in the folder. Please add mp4 files to the folder." + Color.END)
    #wait for user input
    waiting : bool = True
    while (waiting):
        answer: str = input(Color.YELLOW + "Enter a url for a youtube video to download to edit \n or type 'exit' to stop editing \n or type 'yes' if you added a file to the 'to_split' folder \n" + Color.END)
        
        if(answer == "exit"):
            print(Color.GREEN + "exiting video editing..." + Color.END)
            return
        if (answer == "yes"):
            waiting = False
            print(Color.GREEN + "Continuing program..." + Color.END)
            return splitVideos(folder_path, output_directory, chunk_duration, edited_directory) #call the function again to split the video into chunks
        #check if answer is url
        else :
            try:
                print(Color.GREEN + "Downloading video..." + Color.END)
                #print url and folder path we are dolownloading to
                print(Color.BLUE + "URL: " + answer + Color.END)
                print(Color.BLUE + "Save Path: " + folder_path + Color.END)

                print(Color.GREEN + "\n--------------------------------------------" + Color.END)

                #call the download_vid function to download the video
                #downloads the highest quality audio and video
                #saves it to the to_split folder
                download_vid(answer, folder_path)

                #call the function again to split the video, checks if there are mp4 files in the folder, should be since we just downloaded a video
                return splitVideos(folder_path, output_directory, chunk_duration, edited_directory= edited_directory) 
                
            except Exception as e:
                print(Color.RED + "Error downloading video: " + str(e) + Color.END)
                waiting = True





#default to none if no arguments provided
def main(editBool = None, uploadBool = None, gui: bool = False) -> None:

    # Get the current working directory (where your Python script is located)
    project_root = os.getcwd()

    #read title.txt file to print title
    with open('title.txt', 'r') as file:
        title = file.read().strip()
        print(Color.RED + title + Color.END)

    time.sleep(2)

    # Define relative paths from the project root
    folder_path = os.path.join(project_root, "to_split")
    output_directory = os.path.join(project_root, "done_split")
    edited_directory = os.path.join(folder_path, "edited")

    print(Color.GREEN + "Folder path: " + folder_path + Color.END)
    print(Color.GREEN + "Output directory: " + output_directory + Color.END)
    print(Color.GREEN + "Edited directory: " + edited_directory + Color.END)

    
    # Load the config file
    with open('config.json', 'r') as json_file:
        data : dict[str,Any]  = json.load(json_file)

    print(Color.GREEN + "Data: " + str(data) + Color.END)


    tags = data["tags"]
    description = data["description"]
    howManyUploads = data["howManyUploads"]
    howManyHoursBetweenSchedule = data["howManyHoursBetweenSchedule"]
    howManyMinsBetweenUpload = data["howManyMinsBetweenUpload"]
    howManyHoursLongToSleep = data["howManyHoursLongToSleep"]
    MinsBefore = data["sleepXMinsBeforeStartingUploader"]
    chunkDuration = data["chunkDuration"]
    global uploadToYoutube, uploadToInstagram, uploadToTiktok, blurred, useWhisperForTranscription, filterProfanityInSubtitles, firefoxHeadless, tinyLlamaDir, voskModelDir
    uploadToYoutube = data["uploadToYoutube"]
    uploadToInstagram = data["uploadToInstagram"]
    uploadToTiktok = data["uploadToTiktok"]
    blurred = data["blurTopBottomOfClip"]
    useWhisperForTranscription = data["useWhisperForTranscription"]
    filterProfanityInSubtitles= data["filterProfanityInSubtitles"]
    firefoxHeadless = data["firefoxHeadless"]
    voskModelDir = data["voskModelDir"]
    tinyLlamaDir = data["tinyLlamaDir"]

    print(Color.GREEN + "Tags: " + str(tags) + Color.END)
    print(Color.GREEN + "Description: " + description + Color.END)
    print(Color.GREEN + "How many uploads: " + str(howManyUploads) + Color.END)
    print(Color.GREEN + "How many hours between schedule: " + str(howManyHoursBetweenSchedule) + Color.END)
    print(Color.GREEN + "How many minutes between upload: " + str(howManyMinsBetweenUpload) + Color.END)
    print(Color.GREEN + "How many hours long to sleep: " + str(howManyHoursLongToSleep) + Color.END)
    print(Color.GREEN + "Mins Before: " + str(MinsBefore) + Color.END)
    print(Color.GREEN + "Chunk Duration: " + str(chunkDuration) + Color.END)
    print(Color.GREEN + "Upload to Youtube: " + str(uploadToYoutube) + Color.END)
    print(Color.GREEN + "Upload to Instagram: " + str(uploadToInstagram) + Color.END)
    print(Color.GREEN + "Upload to Tiktok: " + str(uploadToTiktok) + Color.END)
    print(Color.GREEN + "Blurred: " + str(blurred) + Color.END)
    print(Color.GREEN + "Use Whisper for Transcription: " + str(useWhisperForTranscription) + Color.END)
    print(Color.GREEN + "Filter Profanity in Subtitles: " + str(filterProfanityInSubtitles) + Color.END)
    print(Color.GREEN + "Firefox Headless: " + str(firefoxHeadless) + Color.END)
    print(Color.GREEN + "Vosk Model Dir: " + str(voskModelDir) + Color.END)
    print(Color.GREEN + "Tiny Llama Dir: " + str(tinyLlamaDir) + Color.END)

    

    
    #if a flag is provided, run the program only for that flag
    if(editBool or uploadBool):
            # Split one of the videos into chunks, move into edited folder
            if editBool:
                splitVideos(folder_path, output_directory, chunkDuration, edited_directory= edited_directory, gui=gui)
                return
            
            # Upload the chunks to YouTube within the done_split folder
            # do this until there are no more videos to upload, then go back to editing
            if uploadBool:
                print(Color.BLUE + "Sleeping for " + str(MinsBefore) + " minutes" + Color.END)
                time.sleep(MinsBefore * 60)
                uploadVideos(output_directory,
                        howManyUploads=howManyUploads,
                        howManyHoursBetweenSchedule=howManyHoursBetweenSchedule,
                        howManyMinsBetweenUpload=howManyMinsBetweenUpload,
                        howManyHoursLongToSleep=howManyHoursLongToSleep,
                        tags=tags,
                        description_video=description)
                return
    
    #else run the program for both flags, edit one vid -> upload -> edit another vid -> upload -> etc
    i : int = 0
    while(True):
        # Split one of the videos into chunks, move into edited folder
        splitVideos(folder_path, output_directory, chunkDuration, edited_directory= edited_directory, gui=gui, splitOneVideo=True) 
        
    
        #Upload the chunks to YouTube within the done_split folder
        #if we are on the first video, sleep for MinsBefore minutes in order to delay the first upload
        if(i == 0):
            print(Color.BLUE + "Sleeping for " + str(MinsBefore) + " minutes" + Color.END)
            #print when next upload will be
            next_upload = datetime.now() + timedelta(seconds=MinsBefore * 60)
            print(Color.BLUE+ f" => next upload at {next_upload}" + Color.END)
            time.sleep(MinsBefore * 60)

        uploadVideos(output_directory,
                    howManyUploads=howManyUploads,
                    howManyHoursBetweenSchedule=howManyHoursBetweenSchedule,
                    howManyMinsBetweenUpload=howManyMinsBetweenUpload,
                    howManyHoursLongToSleep=howManyHoursLongToSleep,
                    tags=tags,
                    description_video=description)
        i +=1

# Run the main function if the name of the module is __main__
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process videos for YouTube.')
    parser.add_argument('--edit', '-e', action='store_true', help='Split videos into chunks. \n \
                        Edits all mp4 files within the to_split folder. \n \
                        Without uploading the videos after editing.')
    parser.add_argument('--upload', '-u', action='store_true', help='Upload video chunks to YouTube. \n \
                        Uploads all mp4 files within the done_split folder.')
    args = parser.parse_args() #parse the arguments, so we can use them in the program, shows up in help message for functions

    if not args.edit and not args.upload:
            print(Color.GREEN+ "\n ---------------------------------------------------------------------" + Color.END)
            print(Color.YELLOW + "\n No arguments provided. \n \
                Defualt functionality is to edit one video into chunks, then upload the chunks to YouTube, and continue edit-upload as a loop. \n \
                Please use --edit to only edit videos from to_split folder, or --upload to only upload videos from done_split folder. \n" + Color.END)


    main(editBool=args.edit, uploadBool=args.upload) #call the main function with the arguments provided
