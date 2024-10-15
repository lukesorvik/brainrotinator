
import os
import subprocess
from moviepy.editor import *
from moviepy.video.fx.all import crop
from moviepy.video.fx.all import resize

from moviepy.video.tools.subtitles import SubtitlesClip

from moviepy.editor import TextClip, CompositeVideoClip, VideoFileClip
import moviepy.video.fx.all as vfx

from transcribe import Transcribe
from moviepy.video.tools.subtitles import SubtitlesClip
import os

import datetime


from termcolor import colored

class VideoEditor:
    def __init__(self, input_path, output_folder, chunk_duration, name : str, useWhisper: bool, filterProfanityInSubtitles: bool, voskModelDir, tinyLlamaDir):
        self.input_path = input_path #input path
        self.output_folder = output_folder #output folder
        self.chunk_duration = chunk_duration #chunk duration
        self.name = name
        self.useWhisper = useWhisper
        self.filterProfanityInSubtitles = filterProfanityInSubtitles
        self.voskModelDir = voskModelDir
        self.tinyLlamaDir = tinyLlamaDir


    
    def split_video_into_chunks(self):
        print(colored(f"\n Splitting video: {self.input_path}", "green"))
        video = VideoFileClip(self.input_path)
        duration = int(video.duration)
        os.makedirs(self.output_folder, exist_ok=True)
        try:
            for start in range(0, duration, self.chunk_duration):
                end = min(start + self.chunk_duration, duration) #end of the chunk
                clip = video.subclip(start, end) # 60 sec chunck we are working with


                # Generate filename based on iteration number (num)
                num = int(end / 60)#if end = 60, num = 1, if end = 120, num = 2... etc
                #convert to string so dont print "1.0"
                numstr = str(num)
                chunckFileName = os.path.join(f"{self.name}_{numstr}")
                videoOutputFileName = os.path.join(self.output_folder, f"{chunckFileName}.mp4") 
                filteredProfanityVideoOutputFileName = os.path.join(self.output_folder, f"{chunckFileName}_filtered.mp4")

                # Check if the file already exists
                if (os.path.exists(filteredProfanityVideoOutputFileName) or os.path.exists(videoOutputFileName)):
                    print(colored(f"File {chunckFileName} already exists. Skipping...", "yellow"))
                    continue  # Skip processing this chunk if file exists


                #crop the chunk to be phone format
                if round((clip.w/clip.h), 4) < 0.5625:
                    # Crop to fit vertical phone screen
                    clip = crop(clip, width=clip.w, height=round(clip.w/0.5625), \
                                x_center=clip.w / 2, \
                                y_center=clip.h / 2)
                else:
                    # Crop to fit horizontal phone screen
                    clip = crop(clip, width=round(0.5625*clip.h), height=clip.h, \
                                x_center=clip.w / 2, \
                                y_center=clip.h / 2)
                #chunk = chunk.resize((1080, 1920))
                clip = resize(clip, height=1920, width=1080)

                project_root = os.getcwd()
                subtitles_path = os.path.join(project_root, "subtitles")
                print("Subtitles path: " + subtitles_path)
                
                #get the audio from the clip
                audio_clip = clip.audio
                mp3_file = os.path.join(subtitles_path, f"{chunckFileName}.mp3")

                # Write the audio to a separate file (so we can convert to srt)
                audio_clip.write_audiofile(mp3_file)

                print(colored(f"Transcribing mp3: {mp3_file}", "yellow"))

                #transcribe the video to srt file, save to subtitles folder
                transcribe = Transcribe(mp3_file, subtitles_path, name=chunckFileName, filterProfanityInSubtitles=self.filterProfanityInSubtitles, voskModelDir=self.voskModelDir, tinyLlamaDir=self.tinyLlamaDir ) #initialize the class with (video_path, output_path)
                if self.useWhisper:
                    print(colored(f"Using Whisper to transcribe", "yellow"))
                    transcribe.transcribeVideoWhisper()
                else:
                    print(colored(f"Using Vosk to transcribe", "yellow"))
                    transcribe.transcribeVideoVosk() 
                #delete mp3 file
                os.remove(mp3_file)

                #path to the srt file
                srtPath = os.path.join(subtitles_path, f"{chunckFileName}.srt") 
                
                font = os.path.join(project_root, "fonts", "Bangers.ttf")
                print("Font path: " + font)

                # text settings for subtitles
                generator = lambda txt: TextClip(
                    txt,
                    font=font,  # Path to Impact font
                    fontsize=150,
                    color="white",
                    stroke_color="black",
                    stroke_width=5,
                )

                #initialize the subtitles
                subtitles = SubtitlesClip(srtPath,generator) 

                #position of the subtitles
                horizontal_subtitles_position = 'center'
                vertical_subtitles_position  = clip.h /4


                #add the subtitles to the video clip
                #movie py doc https://zulko.github.io/moviepy/ref/videotools.html?highlight=subtitles#module-moviepy.video.tools.subtitles
                result = CompositeVideoClip([clip, 
                                            subtitles.set_position((horizontal_subtitles_position, vertical_subtitles_position))])
            
    
                print(colored(f"Saving: {self.name} {numstr}.mp4", "green"))

                #documentation for the parameters for writing the video file https://zulko.github.io/moviepy/ref/VideoClip/VideoClip.html?highlight=write_videofile#moviepy.video.compositing.CompositeVideoClip.CompositeVideoClip.write_videofile
                result.write_videofile(videoOutputFileName, codec="libx264", threads = 24)
                
            
                #how to print colored text in python https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal
                print(colored(f"Saved: {videoOutputFileName} using {srtPath}", "green"))



                #mute parts of videos with swear words
                print(colored(f"Checking for swear words in {videoOutputFileName}", "green"))
            
                #https://github.com/mmguero/cleanvid
                srtFileNameNotClean = os.path.join(subtitles_path, f"{chunckFileName}_notClean.srt")
                currentDir = os.getcwd()
                swearFileName = os.path.join(currentDir ,"swears.txt")
                print(colored(f"swearFileName: {swearFileName}", "yellow"))
                print(colored(f"Using srt: {srtFileNameNotClean} to check for swears", "yellow"))
                

                subprocess.run(["cleanvid", "-s",srtFileNameNotClean, "-i", videoOutputFileName, "-o" ,filteredProfanityVideoOutputFileName, "-w", swearFileName ]
                            , stderr=sys.stderr, stdout=sys.stdout) 
            
                
                #check if filteredProfanityVideoOutputFileName exists
                #no new file will be created if there is no profanity
                if os.path.exists(filteredProfanityVideoOutputFileName):

                    print(colored(f"muted profanity in: {videoOutputFileName} and saved to {filteredProfanityVideoOutputFileName}", "green"))   

                    #delete videoOutputFileName, since we have new good one
                    print(colored(f"Deleting: {videoOutputFileName}", "red"))
                    os.remove(videoOutputFileName)
                else:
                    print(colored(f"No profanity found in: {videoOutputFileName}", "green"))
                print(colored(f"-------------------------------------------", "green"))

        finally:
            # Close the video file, if it is not closed then we cannot move the video file
            video.close()



    def split_video_into_chunks_blur(self):
            print(colored(f"\n Splitting video: {self.input_path}", "green"))
            video = VideoFileClip(self.input_path)
            duration = int(video.duration)
            os.makedirs(self.output_folder, exist_ok=True)
            try:
                for start in range(0, duration, self.chunk_duration):
                    end = min(start + self.chunk_duration, duration) #end of the chunk
                    clip = video.subclip(start, end) # 60 sec chunck we are working with


                    num = int(end / 60)
                    numstr = str(num)  #convert to string so dont print "1.0"
                    chunckFileName = os.path.join(f"{self.name}_{numstr}")
                    videoOutputFileName = os.path.join(self.output_folder, f"{chunckFileName}.mp4") 
                    filteredProfanityVideoOutputFileName = os.path.join(self.output_folder, f"{chunckFileName}_filtered.mp4")

                    # Check if the file already exists
                    if (os.path.exists(filteredProfanityVideoOutputFileName) or os.path.exists(videoOutputFileName)):
                        print(colored(f"File {chunckFileName} already exists. Skipping...", "yellow"))
                        continue  # Skip processing this chunk if file exists
                    
                    print(colored(f"Blurring the video: {videoOutputFileName}", "yellow"))
                    
                    temp_folder = os.path.join(self.output_folder, "temp")
                    tempVideoName = os.path.join(temp_folder, f"temp.mp4")
                    tempVideoName2 = os.path.join(temp_folder, f"temp2.mp4")

                    
                    startTime = seconds_to_time(start)
                    endTime = seconds_to_time(end)
                    print(colored(f"Saving: {tempVideoName} clip using ffmpeg with {startTime} {endTime} ", "yellow"))

                    #call ffmpeg command 
                    #ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:45  tempVideofilename.mp4, no copy so that we do not lag at start
                    subprocess.run(["ffmpeg", "-y","-i", self.input_path, "-ss", startTime, "-to", endTime,  tempVideoName], stderr=sys.stderr, stdout=sys.stdout)

                    print(colored(f"Blurring the video using ffmpeg: {tempVideoName}", "yellow"))
                    subprocess.run([
                        "ffmpeg", 
                        "-y", #force overwrite no prompt
                        "-i", tempVideoName, 
                        "-i", tempVideoName,  # Use the same video for both input files (if needed, adjust as required)
                        "-filter_complex",
                        "[0:v]gblur=sigma=10[blurred];"
                        "[1:v]scale=iw*0.7:ih*0.7[scaled];"
                        "[blurred][scaled]overlay=(W-w)/2:(H-h)/2[overlayed];"
                        "[overlayed]scale= 3413:1920,crop=1080:1920",
                        "-c:a", "copy", 
                        tempVideoName2
                    ], stderr=sys.stderr, stdout=sys.stdout)

                    


                    final_clip = VideoFileClip(tempVideoName2)
                    final_clip = final_clip.set_audio(clip.audio)

                    #-----------------------------------------------------
                    project_root = os.getcwd()
                    subtitles_path = os.path.join(project_root, "subtitles")
                    print("Subtitles path: " + subtitles_path)
                    
                    #get the audio from the clip
                    audio_clip = clip.audio
                    mp3_file = os.path.join(subtitles_path, f"{chunckFileName}.mp3")

                    # Write the audio to a separate file (so we can convert to srt)
                    audio_clip.write_audiofile(mp3_file)

                    print(colored(f"Transcribing mp3: {mp3_file}", "yellow"))

                    transcribe = Transcribe(mp3_file, subtitles_path, name=chunckFileName, filterProfanityInSubtitles=self.filterProfanityInSubtitles,voskModelDir=self.voskModelDir, tinyLlamaDir=self.tinyLlamaDir ) #initialize the class with (video_path, output_path)
                    if self.useWhisper:
                        print(colored(f"Using Whisper to transcribe", "yellow"))
                        transcribe.transcribeVideoWhisper()
                    else:
                        print(colored(f"Using Vosk to transcribe", "yellow"))
                        transcribe.transcribeVideoVosk() 
                        
                    #delete mp3 file
                    os.remove(mp3_file)

                    #path to the srt file
                    srtPath = os.path.join(subtitles_path, f"{chunckFileName}.srt") 
                    
                    font = os.path.join(project_root, "fonts", "Bangers.ttf")
                    print("Font path: " + font)

                    # text settings for subtitles
                    generator = lambda txt: TextClip(
                        txt,
                        font=font,  # Path to Impact font
                        fontsize=150,
                        color="white",
                        stroke_color="black",
                        stroke_width=5,
                    )

                    #initialize the subtitles
                    subtitles = SubtitlesClip(srtPath,generator) 

                    #position of the subtitles
                    horizontal_subtitles_position = 'center'
                    vertical_subtitles_position  = final_clip.h /6

                    #add the subtitles to the video clip
                    result = CompositeVideoClip([final_clip, 
                                                subtitles.set_position((horizontal_subtitles_position, vertical_subtitles_position))])
                
                    #save video with subtitles
                    print(colored(f"Saving Subtitles to the video: {self.name} {numstr}.mp4", "yellow"))
                    result.write_videofile(videoOutputFileName, codec="libx264", threads = 24)
                    print(colored(f"Saved: {videoOutputFileName} using {srtPath}", "green"))
                    print(colored(f"Checking for swear words in {videoOutputFileName}", "yellow"))
                
                    #https://github.com/mmguero/cleanvid
                    srtFileNameNotClean = os.path.join(subtitles_path, f"{chunckFileName}_notClean.srt")
                    currentDir = os.getcwd()
                    swearFileName = os.path.join(currentDir ,"swears.txt")
                    print(colored(f"swearFileName: {swearFileName}", "yellow"))
                    print(colored(f"Using srt: {srtFileNameNotClean} to check for swears", "yellow"))
                    

                    subprocess.run(["cleanvid", "-s",srtFileNameNotClean, "-i", videoOutputFileName, "-o" ,filteredProfanityVideoOutputFileName, "-w", swearFileName ]
                                , stderr=sys.stderr, stdout=sys.stdout) 
                    
                    
                    if os.path.exists(filteredProfanityVideoOutputFileName):
                        print(colored(f"muted profanity in: {videoOutputFileName} and saved to {filteredProfanityVideoOutputFileName}", "green"))   
                        print(colored(f"Deleting: {videoOutputFileName}", "red"))
                        os.remove(videoOutputFileName)
                    else:
                        print(colored(f"No profanity found in: {videoOutputFileName}", "green"))
                    print(colored(f"-------------------------------------------", "green"))

            finally:
                # Close the video file, if it is not closed then we cannot move the video file
                video.close()
                


#helper function to convert seconds to time
def seconds_to_time(seconds):
    return str(datetime.timedelta(seconds=seconds))