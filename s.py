from vosk import Model, KaldiRecognizer
import pynput.keyboard as keyboard
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
rec_key = keyboard.Key.space
visual_inp_delay = 5

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

def path(file):
    global ROOT_PATH
    return f"{ROOT_PATH}\\{file}"

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
        self.init_ui()
        self.init_input()

    def init_ui(self):
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

    def init_input(self):
        self.inp = VoiceRec(self.tray)
        self.inp.pressed.connect(self.hide_input_window)
        self.inp.gotText.connect(self.show_input_window)

        title = "Ready!"
        message = "The app is ready!"
        self.tray.showMessage(title, message)
        
    def show_input_window(self, text):
        if text:
            self.clipboard.clear()
            text = text_post_proc(text)
            self.clipboard.setText(text)
            self.input_window = VisualInput(text)
            self.timer = Timer(visual_inp_delay, self.input_window.close)
            self.timer.start()

    def hide_input_window(self):
        try:
            self.timer.cancel()
            self.input_window.close()
        except AttributeError:
            pass

    def close(self):
        self.hide_input_window()
        self.inp.close()
        QApplication.quit()

class VisualInput(QWidget):
    def __init__(self, text):
        super().__init__()

        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setGeometry(700, 30, 100, 30)
       
        self.text = QLabel()
        self.text.setText(text)

        self.layout = QGridLayout()
        self.layout.addWidget(self.text, 0, 0)
        self.setLayout(self.layout)

        self.show()

class KeyListener(QObject):

    pressed = pyqtSignal()

    def __init__(self, parent_VoiceRec):
        super().__init__()
        self.setParent(parent_VoiceRec)

        self.PRESSED = False

        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def on_press(self, key):
        if key == rec_key:
            if not self.PRESSED:
                self.PRESSED = True
                self.pressed.emit()

    def on_release(self, key):
        if key == rec_key:
            self.PRESSED = False

    def close(self):
        self.listener.stop()

class VoiceRec(QObject):

    pressed = pyqtSignal()
    gotText = pyqtSignal(str)

    def __init__(self, parent_QSystemTrayIcon):
        super().__init__()
        self.setParent(parent_QSystemTrayIcon)

        if not os.path.exists(path("vosk-model-small-ru-0.22")):
            #print("Model not found.")
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
        self.listener = KeyListener(self)
        self.listener.pressed.connect(self.record)

    def record(self):
        self.pressed.emit()
        self.stream.start_stream()
        raw_data = bytes()
        while self.listener.PRESSED:
            data = self.stream.read(chunk)
            raw_data += data
        self.stream.stop_stream()
        if len(raw_data) > 0:
            self.rec.AcceptWaveform(raw_data)
            raw_text = self.rec.FinalResult()
            raw_text = json.loads(raw_text)
            raw_text = raw_text["text"]
            if raw_text:
                self.gotText.emit(raw_text)
                return
        self.gotText.emit('')

    def close(self):
        self.listener.close()
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

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