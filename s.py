from vosk import Model, KaldiRecognizer
from pynput.keyboard import Key, Listener
import pyaudio
import json
import os, sys
import re
from threading import Thread, Timer
from PyQt5.QtWidgets import (QApplication, QMenu, 
                             QAction, QSystemTrayIcon, 
                             QMessageBox, QWidget,
                             QLabel, QGridLayout)
from PyQt5.QtGui import QIcon, QGuiApplication
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from collections import OrderedDict

rate = 16000
chunk = 4000
rec_key = Key.space
PRESSED = False
STOPPED = False
visual_inp_delay = 5

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

def path(file):
    global ROOT_PATH
    return f"{ROOT_PATH}\\{file}"

def msg():
    m = QMessageBox()
    m.setWindowTitle("Info")
    m.setText("Your text here!")
    m.exec()

def text_post_proc(text):
    # Replace
    for key in list(repl.keys()):
        if key in text:
            text = text.split(key)
            text = [elem.strip() for elem in text]
            text = repl[key].join(text)
    # Capitalize
    inds = [m.end(0) for m in re.finditer(r"[.!?]\s", text)] + [len(text)]
    text_l = []
    fr = to = 0
    for ind in inds:
        fr = to
        to = ind
        text_l.append(text[fr:to])
    text = [elem.capitalize() for elem in text_l]
    text = ''.join(text)
    return text

class TrayUI:
    def __init__(self):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(path("icon.png")))
        self.tray.setVisible(True)

        self.a_quit = QAction("Quit")
        self.a_quit.setIcon(QIcon(path("close.png")))
        self.a_quit.triggered.connect(self.close)

        self.menu = QMenu()
        self.menu.addAction(self.a_quit)

        self.tray.setContextMenu(self.menu)
        self.menu.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tray.activated.connect(self.menu.exec_)

        self.clipboard = QGuiApplication.clipboard()
        self.start_input_thread()

    def start_input_thread(self):
        self.inp_thread = VoiceRec()
        self.inp_thread.gotText.connect(self.show_input_window)
        self.inp_thread.start()

    def show_input_window(self, text):
        self.hide_input_window()
        text = text_post_proc(text)
        self.clipboard.setText(text)
        self.input_window = VisualInput()
        self.input_window.text_mode(text)
        self.timer = Timer(visual_inp_delay, self.input_window.close)
        self.timer.start()

    def hide_input_window(self):
        try:
            self.timer.cancel()
            self.input_window.close()
        except AttributeError:
            pass
        self.clipboard.clear()

    def close(self):
        global STOPPED
        STOPPED = True
        self.hide_input_window()
        self.inp_thread.join()
        QApplication.quit()

class VisualInput(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setGeometry(700, 30, 100, 30)
        self.show()

    def text_mode(self, text):
        t = QLabel()
        t.setText(text)
        layout = QGridLayout()
        layout.addWidget(t, 0, 0)
        self.setLayout(layout)

    def wait_mode(self):
        pass

class VoiceRec(QObject, Thread):

    gotText = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        if not os.path.exists(path("vosk-model-small-ru-0.22")):
            print("Model not found.")
            exit(1)
        self.model = Model(path("vosk-model-small-ru-0.22")) 

        self.rec = KaldiRecognizer(self.model, rate)
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16, 
            channels=1, 
            rate=rate, 
            input=True, 
            frames_per_buffer=chunk
        )
        self.listener = Listener(
                on_press=self.on_press,
                on_release=self.on_release
        )
        #print("Ready!") ###############

    def run(self):
        self.listener.start()
        try:
            while not STOPPED:
                if PRESSED:
                    #print(self.record())
                    text = self.record()
                    self.gotText.emit(text)
        finally:
            self.listener.stop()
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

    def on_press(self, key):
        global PRESSED
        if key == rec_key:
            PRESSED = True

    def on_release(self, key):
        global PRESSED, STOPPED
        if key == rec_key:
            PRESSED = False

    def record(self):
        global PRESSED
        self.stream.start_stream()
        raw_data = bytes()
        while PRESSED:
            data = self.stream.read(chunk)
            raw_data += data
        self.stream.stop_stream()
        if len(raw_data) > 0:
            self.rec.AcceptWaveform(raw_data)
            raw_text = self.rec.FinalResult()
            raw_text = json.loads(raw_text)
            raw_text = raw_text["text"]
        return raw_text

repl = OrderedDict({
# Punctuation
    'точка с запятой': '; ',
    'точка': '. ',
    'запятая': ', ',
    'восклицательный знак': '! ',
    'вопросительный знак': '? ',
    'двоеточие': ': ',
    'многоточие': '... ',
    'тире': ' — ',
    'дефис': '-',
})

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ui = TrayUI()
    sys.exit(app.exec_())