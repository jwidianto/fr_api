
import cv2
import numpy as np
import base64
import requests
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics.texture import Texture
from kivy.clock import Clock


class FaceAbsenApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capture = cv2.VideoCapture(0)
        self.port = "10.0.0.206:8006"
        self.is_in = True
        self.is_loading = False
        self.is_ok = False
        self.captured_image = None
        self.dnik = " "
        self.drespon = "......"
        self.dnama = " "
        self.duuid = "......"
        self.timer = None
        self.is_active = True
        self.waiting_for_action = False

    def build(self):
        self.layout = FloatLayout()
        
        # camera view
        self.image_widget = Image(size_hint=(1, 1), allow_stretch=True)
        self.layout.add_widget(self.image_widget)
        
        # Main Frame
        self.main_frame = FloatLayout(size_hint=(None, None), size=(200, 100), pos_hint={'right': 1, 'top': 1})
        
        # IN/OUT button
        self.inout_button = Button(text="IN", on_press=self.ganti_inout, size_hint=(None, None), size=(100, 50), pos_hint={'right': 1, 'top': 1})
        self.inout_button.background_normal = ''
        self.inout_button.background_color = (0, 0.5, 0, 1)  # Default green color
        self.layout.add_widget(self.inout_button)
        
        # Response Frame
        self.response_frame = FloatLayout(size_hint=(None, None), size=(400, 200), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        
        # Response Label
        self.response_label = Label(text=self.drespon, size_hint_y=None, height=50, size_hint_x=1, pos_hint={'center_x': 0.5, 'center_y': 0.7}, halign='center', valign='middle')
        self.response_frame.add_widget(self.response_label)
        
        # Name Label
        self.name_label = Label(text=self.dnama, size_hint_y=None, height=50, size_hint_x=1, pos_hint={'center_x': 0.5, 'center_y': 0.5}, halign='center', valign='middle')
        self.response_frame.add_widget(self.name_label)
        
        # Yes/No buttons
        self.yes_button = Button(text="YES", on_press=self.is_yes_button, size_hint=(None, None), size=(150, 50), pos_hint={'center_x': 0.35, 'center_y': 0.3})
        self.yes_button.background_normal = ''
        self.yes_button.background_color = (0, 1, 0, 1)
        self.yes_button.border_radius = [25] * 4
        self.response_frame.add_widget(self.yes_button)
        
        self.no_button = Button(text="NO", on_press=self.is_no_button, size_hint=(None, None), size=(150, 50), pos_hint={'center_x': 0.65, 'center_y': 0.3})
        self.no_button.background_normal = ''
        self.no_button.background_color = (1, 0, 0, 1)
        self.no_button.border_radius = [25] * 4
        self.response_frame.add_widget(self.no_button)
        
        # hide Response Frame
        self.response_frame.opacity = 0
        self.layout.add_widget(self.response_frame)
        
        Clock.schedule_interval(self.update, 1.0 / 30.0)
        return self.layout

    def ganti_inout(self, instance):
        self.is_in = not self.is_in
        self.inout_button.text = "IN" if self.is_in else "OUT"
        self.inout_button.background_color = (0, 0.5, 0, 1) if self.is_in else (1, 0, 0, 1)

    def update(self, dt):
        if not self.waiting_for_action:
            ret, frame = self.capture.read()
            if ret:
                buf = cv2.flip(frame, 0).tostring()
                texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                self.image_widget.texture = texture
                
                if self.detect_face(frame):
                    self.captured_image = frame
                    self.check_image()
                    self.waiting_for_action = True
                    self.response_frame.opacity = 1
        else:
            pass

    def detect_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        return len(faces) > 0

    def check_image(self):
        if self.captured_image is not None:
            _, buffer = cv2.imencode('.jpg', self.captured_image)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            payload = {"file": base64_image}
            response = requests.post(f"http://{self.port}/verify64", json=payload)
            self.process_response(response.json())

    def process_response(self, response):
        if response.get("success"):
            self.dnik = response["induk"]
            self.drespon = f"NIK: {response['induk']}"
            self.dnama = response["nama"]
            self.duuid = response["uuid"]
            self.is_ok = True
        else:
            self.drespon = "Data belum akurat, silahkan coba lagi."
            self.dnama = " "
            Clock.schedule_once(lambda dt: self.reset_to_main(), 2)
        self.update_labels()

    def update_labels(self):
        self.response_label.text = self.drespon
        self.name_label.text = self.dnama

    def is_yes_button(self, instance):
        if self.is_ok:
            status = "I" if self.is_in else "O"
            payload = {"uuid": self.duuid, "nik": self.dnik, "in_out": status, "mac_address": self.port}
            response = requests.post(f"http://{self.port}/absensi64", json=payload)
            self.process_absen_response(response.json())

    def process_absen_response(self, response):
        if response.get("success"):
            self.drespon = "Success"
        else:
            self.drespon = "Failed"
        self.update_labels()
        self.reset_to_main()

    def is_no_button(self, instance):
        self.captured_image = None
        self.is_ok = False
        self.drespon = "......"
        self.dnama = " "
        self.update_labels()
        self.reset_to_main()

    def reset_to_main(self):
        self.waiting_for_action = False
        self.response_frame.opacity = 0
        self.captured_image = None
        self.drespon = "......"
        self.dnama = " "
        self.update_labels()

if __name__ == '__main__':
    FaceAbsenApp().run()






