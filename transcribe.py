from io import BytesIO
import json
import re
import subprocess
import sys

import requests

import torch
from vosk import Model, KaldiRecognizer, SetLogLevel
import os

from termcolor import colored
import profanity
import whisper
from whisper.utils import get_writer
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import zipfile


class Transcribe:
    #@param output_path - path to the output srt file
    def __init__(self, audioPath, output_path, name, filterProfanityInSubtitles: bool, voskModelDir, tinyLlamaDir):
        self.audioPath = audioPath #path for where the mp3 file is
        self.output_path = output_path #subtitles save path
        self.name = name #name of the video (so we can name the srt correctly)
        self.filterProfanityInSubtitles = filterProfanityInSubtitles #if true, then we filter out profanity in the subtitles
        self.tinyLlamaDir = tinyLlamaDir
        self.voskModelDir = voskModelDir

    

    def transcribeVideoVosk(self) -> None:
        #transcribe the video to srt file
        print(colored("Transcribing video...", "green"))

        unFilteredSrtFileName = os.path.join(self.output_path, f"{self.name}_notClean.srt")
        print(colored(f"File name: {unFilteredSrtFileName}", "yellow"))
        #check if the file already exists, if it does then return
        if os.path.exists(unFilteredSrtFileName):
            print(colored("SRT file already exists. Skipping...", "red"))
            return

      

        currentWorkingDirectory = os.getcwd()


        #vosk model
        #------------------------------------------------------------------------------------

        
        #if model does not exist, download it
        #RUN apt-get install -y unzip \
            
        #if voskmodel directory is empty string, not provided used working diretory
        voskDir = ''
        if not self.voskModelDir:
            voskDir= currentWorkingDirectory
        else:
            voskDir = self.voskModelDir
        
        modelPath = os.path.join(voskDir, "vosk-model-en-us-0.42-gigaspeech")
        url = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip"
        zip_filename = "vosk-model-en-us-0.42-gigaspeech.zip"

        if not os.path.exists(modelPath):
            print(f"Downloading model from {url}...")
            
            # Download the file
            response = requests.get(url)
            with open(zip_filename, 'wb') as file:
                file.write(response.content)
            print("Download completed.")

            # Extract the ZIP file
            print("Extracting the ZIP file...")
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(currentWorkingDirectory)
            print("Extraction completed.")

            # Remove the ZIP file
            os.remove(zip_filename)
            print("ZIP file removed.")
        else:
            print(f"Model already exists at {modelPath}.")
            
        
        SAMPLE_RATE = 16000

        SetLogLevel(-1)

        print("Vosk model path: ", modelPath)
        subtitles = ''
        model = Model(model_path=modelPath)
        rec = KaldiRecognizer(model, SAMPLE_RATE)
        rec.SetWords(True)

     
       
        with subprocess.Popen(["ffmpeg", "-loglevel", "quiet", "-i",
                                    self.audioPath,
                                    "-ar", str(SAMPLE_RATE) , "-ac", "1", "-f", "s16le", "-"],
                                    stdout=subprocess.PIPE).stdout as stream:
            data = stream.read()
            stream = BytesIO(data) #have to copy the stream into a buffer in memory
            subtitles = rec.SrtResult(stream, words_per_line=1) #srt save has to be first read from stream or the timestamp will be wrong
            print(subtitles)
            
            result : str = extract_words_from_srt(None, subtitles)
            print(result)
            stream.close()
            
            f= open(unFilteredSrtFileName, "w")
            f.write(subtitles)
            f.close()
            print(colored(f"Subtitles saved to {unFilteredSrtFileName}", "yellow"))
            
            transcriptionPath = os.path.join(self.output_path, f"{self.name}_transcription.txt")
            with open(transcriptionPath, "w") as f:
                f.write(result)
                f.close()
        #------------------------------------------------------------------------------------
       
        
        #Filter out profanity in the subtitles, then save
        #if profanity filter off do not filter
        cleanSrtFileName = os.path.join(self.output_path, f"{self.name}.srt")
        f = open(cleanSrtFileName, "w")
        if self.filterProfanityInSubtitles:
            subtitles  = self.filterProfanity(subtitles) 
        f.write(subtitles)
        f.close()
        print(colored(f"Subtitles saved to {cleanSrtFileName}", "yellow"))
         #------------------------------------------------------------------------------------

        #get the Ai summary
        summary :str = self.llmSummarize(result)
        print(colored(f"Summary before: {summary}", "yellow"))
        summary = self.filterProfanity(summary) #filter out profanity
        summary = summary.replace("\"", "") #regex any " within summary
        print(colored(f"Summary after all filters: {summary}", "green"))
        summary_save_path = os.path.join(self.output_path, f"{self.name}_summary.txt")
        f = open(summary_save_path, "w")
        f.write(summary)
        f.close()
        print(colored(f"Summary saved to {summary_save_path}", "yellow"))


        print(colored("Transcription complete.", "green"))
        
    def transcribeVideoWhisper(self) -> None:
        #transcribe the video to srt file
        print(colored("Transcribing video...", "green"))


        unFilteredSrtFileName = os.path.join(self.output_path, f"{self.name}_notClean.srt")
        print(colored(f"File name: {unFilteredSrtFileName}", "yellow"))
        if os.path.exists(unFilteredSrtFileName):
            print(colored("SRT file already exists. Skipping...", "red"))
            return

        currentWorkingDirectory = os.getcwd()

        
        #Whisper model
        #------------------------------------------------------------------------------------
        subtitles = ''
        model_name = "large-v3"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model(model_name).to(device)
        filename =self.name + "_notClean.srt"

        language = "en" if model_name.endswith(".en") else None
        subtitles : dict = model.transcribe(self.audioPath, language=language, temperature=0.0, word_timestamps=True)

        transcript = str(subtitles["text"])
        print(subtitles)
        print(colored(f"Transcript: {transcript}", "yellow"))
        
        transcriptionPath = os.path.join(self.output_path, f"{self.name}_transcription.txt")
        with open(transcriptionPath, "w") as f:
            f.write(transcript)
            f.close()
        
        writer = get_writer("srt", output_dir=self.output_path) #returns a writer object
        writer(subtitles, filename,  max_words_per_line=1 ) #writes the result to the file, specify keyword argument (kwargs) to set max words per line
        
        del model
        torch.cuda.empty_cache()
        #------------------------------------------------------------------------------------
        
        with open(unFilteredSrtFileName, "r") as f:
            subtitles = f.read()
            f.close()
        print(subtitles)
        
        #filter out profanity, then save
        #we use this srt for the final video, and the unfiltered srt for detecting when to mute profanity
        cleanSrtFileName = os.path.join(self.output_path, f"{self.name}.srt")
        f = open(cleanSrtFileName, "w")
        if self.filterProfanityInSubtitles:
            subtitles  = self.filterProfanity(subtitles) 
        f.write(subtitles)
        f.close()
        print(colored(f"Subtitles saved to {cleanSrtFileName}", "yellow"))
         #------------------------------------------------------------------------------------

        #Get the Ai summary
        summary :str = self.llmSummarize(transcript)
        print(colored(f"Summary before: {summary}", "yellow"))
        #filter out profanity in the summary
        summary = self.filterProfanity(summary) 
        summary = summary.replace("\"", "") #regex any " within summary
        print(colored(f"Summary after all filters: {summary}", "green"))
        summary_save_path = os.path.join(self.output_path, f"{self.name}_summary.txt")
        f = open(summary_save_path, "w")
        f.write(summary)
        f.close()
        print(colored(f"Summary saved to {summary_save_path}", "yellow"))


        print(colored("Transcription complete.", "green"))

    def filterProfanity (self, input: str) -> str :
        print(colored("Filtering profanity...", "green"))
        profanity.set_censor_characters("*#@!")
        
        #Set swearWords to the contents of the file
        swearsFileLocation = os.path.join(os.getcwd(), "swears.txt")
        print(colored(f"swearsFileLocation: {swearsFileLocation}", "yellow"))
        f = open(swearsFileLocation, "r")
        swearWords = f.readlines()
        swearWords = [w.strip() for w in swearWords if w]
        f.close()
        profanity.load_words(swearWords)
        #print(swearWords)
        
        return profanity.censor(input)
    

    def llmSummarize(self, input:str) -> None:
        print(colored("Summarizing text using Tinyllama...", "green"))
        llamaDir = ''
        
        if not self.tinyLlamaDir:  #if tinyLlamaDir is empty string, use current working directory
            llamaDir= os.getcwd()
        else:
            llamaDir = self.tinyLlamaDir
            
        localModelPath = os.path.join(llamaDir, "models--TinyLlama--TinyLlama-1.1B-Chat-v1.0")
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

        if not os.path.exists(localModelPath):
            print(f"Downloading model from {model_name} to {localModelPath}...")
            model = AutoModelForCausalLM.from_pretrained(model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model.save_pretrained(localModelPath)
            tokenizer.save_pretrained(localModelPath)
        else:
            print(f"Model already exists at {localModelPath}.")
        
        
        pipe = pipeline("text-generation", model=localModelPath, torch_dtype=torch.bfloat16, device_map="auto")
        input = input + "\n Summarize the above transcript into a catchy title for youtube. Do not include any additional text before or after the title. Make the title one sentence long."
        
        
        # We use the tokenizer's chat template to format each message - see https://huggingface.co/docs/transformers/main/en/chat_templating
        messages = [
            {
                "role": "system",
                "content": "You always respond with one catchy youtube title, no longer than one sentence. Do not include any additional text before or after the title.",
            },
            {"role": "user", "content": input},
        ]
        prompt = pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        outputs = pipe(prompt, max_new_tokens=256, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
        generatedText = outputs[0]["generated_text"]
        print(generatedText)
        #keep anything after <|assistant|> in the output
        generatedText = generatedText.split("<|assistant|>")[1]
        print(colored(f"{generatedText}", "yellow"))
        
        del pipe
        torch.cuda.empty_cache()
        
        #filter out any whitespace before
        generatedText = generatedText.strip()
        #only include the /line in string
        generatedText = generatedText.split("\n")[0]
        
                
        #filter out any mention of catchy youube title that chatbot sometimes includes
        generatedText = re.sub(r'(?i)Catchy YouTube title', '', generatedText)
        generatedText = re.sub(r'(?i)YouTube Title', '', generatedText)
        generatedText = re.sub(r'(?i)Chatbot', '', generatedText)
        generatedText = re.sub(r'(?i)one sentence', '', generatedText)
        
        print(colored(f"Ai title after filter out catchy youtube title: \n{generatedText}", "green"))
        
        #filter any whitespace after
        generatedText = generatedText.strip()
        
        print(colored(f"Ai title after filter whitespace & only include first line: \n{generatedText}", "green"))
        
        #truncate the text to 100 characters (youtbe limits titles to 100 chars)
        generatedText = generatedText[:100]
        print(colored(f" \n Ai title after trunkate to 100 chars: \n {generatedText} \n", "yellow"))
        

        
        return generatedText
    
def extract_words_from_srt(srt_file = None, input:str = None):
    
    content =''
    if srt_file:
        with open(srt_file, 'r', encoding='utf-8') as file:
            content = file.read()
    if input:
        content = input
    # Remove numbers (sequence numbers), timestamps, and extra lines
    cleaned_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
    
    # Remove any remaining empty lines or numbers
    cleaned_text = re.sub(r'\n\d+\n', '\n', cleaned_text)
    
    # Remove any leftover newlines that appear more than twice in a row
    cleaned_text = re.sub(r'\n+', '\n', cleaned_text).strip()
    
    #merge all lines into one line
    cleaned_text = cleaned_text.replace("\n", " ")
    
    return cleaned_text


    