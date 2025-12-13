from openwakeword.model import Model
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import time
from scipy.io.wavfile import write
import os

WHISPER_SIZE = "base"
CHUNK = 1280 # 80ms @ 16kHz
FS = 16000 # Mic sample rate (Hz)
WAV_PATH = "utterance.wav"
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
        audio, _ = stream.read(CHUNK)
        pcm = audio.flatten().astype(np.int16)
        frames.append(pcm)

        level = rms_int16(pcm)
        if level < SILENCE_RMS:
            silent_for += CHUNK / FS
        else:
            silent_for = 0.0

        if silent_for >= SILENCE_SECONDS:
            break
        if (time.time() - start) >= MAX_RECORD_SECONDS:
            break

    return np.concatenate(frames)


def main():
    wake = Model()
    stt = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")

    print("Listening for wake word...")
    with sd.InputStream(samplerate=FS, channels=1, dtype="int16", blocksize=CHUNK) as stream:
        while True:
            audio, _ = stream.read(CHUNK)
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
                write(WAV_PATH, FS, utterance)

                try:
                    print("Transcribing...")
                    segments, _ = stt.transcribe(WAV_PATH)
                    text = " ".join(seg.text.strip() for seg in segments).strip()

                    if text:
                        print("You said:", text)
                    else:
                        print("Heard nothing useful.")
                finally:
                    if os.path.exists(WAV_PATH):
                        os.remove(WAV_PATH)

                print("\nListening for wake word...")


if __name__ == "__main__":
    main()
