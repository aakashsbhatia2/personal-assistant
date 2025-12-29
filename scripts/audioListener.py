"""
Script to listen for wake word and process audio
"""

# Speech to Text (Whisper + Open Wake Word)
from openwakeword.model import Model
from faster_whisper import WhisperModel

# Audio processing (Sound Device)
import sounddevice as sd

# Text to Speech (Wave + Piper)
import wave
from piper import PiperVoice

# Misc utilities
import numpy as np
import time
from scipy.io.wavfile import write
import os
import subprocess

# API calls
import requests

# env vars
from dotenv import load_dotenv
load_dotenv()

# constants
from constants import ASSISTANT_SYSTEM_PROMPT

# Finetuning constants
WHISPER_SIZE = "base" # Whisper model
BLOCK_SIZE = 1280 # 80ms @ 16kHz
SAMPLE_RATE = 16000 # Mic sample rate (Hz)
WAV_FILE_PATH = "audio_file.wav"
WAKE_THRESH = 0.6 # Wake-word probability threshold
SILENCE_SECONDS = 3.0 # Stop after this much silence
MAX_RECORD_SECONDS = 8.0 # Max utterance length
SILENCE_RMS = 700 # Silence loudness threshold
TARGET_WAKEWORD = "hey_jarvis"
WAKE_DEBOUNCE_FRAMES = 4 # require this many consecutive chunks above threshold

def rms_int16(x):
    x = x.astype(np.float32)
    return np.sqrt(np.mean(x * x))

def record_until_silence(stream) -> np.ndarray:
    frames = []
    silent_for = 0.0
    start = time.time()

    while True:
        audio, _ = stream.read(BLOCK_SIZE)
        pcm = audio.flatten().astype(np.int16)
        frames.append(pcm)

        level = rms_int16(pcm)
        if level < SILENCE_RMS:
            silent_for += BLOCK_SIZE / SAMPLE_RATE
        else:
            silent_for = 0.0

        if silent_for >= SILENCE_SECONDS:
            break
        if (time.time() - start) >= MAX_RECORD_SECONDS:
            break

    return np.concatenate(frames)

def queryOllama(command) :
    url = 'http://localhost:11434/api'
    params = {
        'model': 'llama3.2:1b',
        'stream': False,
        'messages': [
            {
                'role': 'user',
                'content': command
            },
            {
                'role': 'system',
                'content': ASSISTANT_SYSTEM_PROMPT
            }
        ]
    }
    response = requests.post(url + '/chat', json=params)

    print(response.json()['message']['content'])

def sendQueryToServer(command):
    url = 'http://localhost:8000/assistant'
    response = requests.post(url, json={ 'text': command })
    print(response.json())


def main():
    # TTS
    wake = Model()
    stt = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")

    # STT
    voice = PiperVoice.load("./en_US-lessac-medium.onnx", config_path="./en_US-lessac-medium.onnx.json")

    command = 'Turn off the lights in bathroom 2'
    sendQueryToServer(command)
    queryOllama(command)
    return


    print("Listening for wake word...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK_SIZE) as stream:
        while True:
            audio, _ = stream.read(BLOCK_SIZE)
            pcm = audio.flatten().astype(np.int16)

            scores = wake.predict(pcm)

            score = float(scores.get(TARGET_WAKEWORD, 0.0))
            
            if score >= WAKE_THRESH:
                consecutive += 1
            else:
                consecutive = 0

            if consecutive >= WAKE_DEBOUNCE_FRAMES:
                consecutive = 0
                print("Wake word detected. Speak now...")

                utterance = record_until_silence(stream)
                write(WAV_FILE_PATH, SAMPLE_RATE, utterance)

                try:
                    print("Transcribing...")
                    segments, _ = stt.transcribe(WAV_FILE_PATH)
                    text = " ".join(seg.text.strip() for seg in segments).strip()

                    if text:
                        print("You said:", text)

                        with wave.open(WAV_FILE_PATH, "wb") as wav_file:
                            print(wav_file)

                            voice.synthesize_wav(text, wav_file)

                        subprocess.run(["aplay", WAV_FILE_PATH], check=False)
                    else:
                        print("Heard nothing useful.")
                finally:
                    if os.path.exists(WAV_FILE_PATH):
                        os.remove(WAV_FILE_PATH)

                print("\nListening for wake word...")


if __name__ == "__main__":
    main()
