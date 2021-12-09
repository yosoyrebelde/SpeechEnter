from vosk import Model, KaldiRecognizer
from pynput.keyboard import Key, Listener
import pyaudio
import json
import os, sys

rate = 16000
chunk = 4000
rec_key = Key.space
PRESSED = False
STOPPED = False

def on_press(key):
    global PRESSED
    if key == rec_key:
        PRESSED = True

def on_release(key):
    global PRESSED, STOPPED
    if key == rec_key:
        PRESSED = False
    elif key == Key.esc:
        STOPPED = True

def input():
    global rec, stream
    global PRESSED
    stream.start_stream()
    raw_data = bytes()
    while PRESSED:
        data = stream.read(chunk)
        raw_data += data
    stream.stop_stream()
    if len(raw_data) > 0:
        rec.AcceptWaveform(raw_data)
        raw_text = rec.FinalResult()
        raw_text = json.loads(raw_text)
        raw_text = raw_text["text"]
    return raw_text

if not os.path.exists(r"C:\py\speech\vosk-model-small-ru-0.22"):
    print("Model not found.")
    exit(1)
model = Model(r"C:\py\speech\vosk-model-small-ru-0.22") 

rec = KaldiRecognizer(model, rate)
p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16, 
    channels=1, 
    rate=rate, 
    input=True, 
    frames_per_buffer=chunk
)
listener = Listener(
        on_press=on_press,
        on_release=on_release
)
listener.start()

print("Ready!")

try:
    while not STOPPED:
        if PRESSED:
            print(input())
finally:
    listener.stop()
    stream.stop_stream()
    stream.close()
    p.terminate()
