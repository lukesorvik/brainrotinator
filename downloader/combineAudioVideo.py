import os
import subprocess

"""
Function to combine the audio and video of a video using ffmpeg-python
@param videoPath: the path to the video
@param audioPath: the path to the audio
@param outputPath: the path to save the output to
@param outputName: the name of the output file
"""
def CombineAudioVideo(videoPath, audioPath, outputPath, outputName):
    try:
        outputFilePath = os.path.join(outputPath, outputName)


        subprocess_command = [
        'ffmpeg',
        '-y',                # Overwrite output file without asking
        '-i', videoPath,     # Input video
        '-i', audioPath,     # Input audio
        '-c', 'copy',        # Codec copy (no re-encoding)
        outputFilePath       # Output path
        ]

        subprocess.run(subprocess_command, check=True)

        print(f"Combined audio and video saved to: {outputFilePath}")

    except Exception as e:
        print(f"Error combining audio and video: {e}")
