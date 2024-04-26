import socket
import threading
from scene import *
import struct
import os
import sound
import time

PORT = 12345
text_to_display = ""
audio_file_path = ""

def receive_data():
    global text_to_display, audio_file_path
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', PORT))
        s.listen(1)  # 只允许一个连接在队列中等待
        while True:
            conn, addr = s.accept()
            with conn:
                data = b""
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                kaomoji_len = struct.unpack('!I', data[:4])[0]
                kaomoji_data = data[4:4+kaomoji_len]
                audio_len = struct.unpack('!I', data[4+kaomoji_len:8+kaomoji_len])[0]
                audio_data = data[8+kaomoji_len:8+kaomoji_len+audio_len]
                text_to_display = kaomoji_data.decode()
                
                # Create a new uniquely named audio file in the Documents directory
                timestamp = int(time.time())
                documents_dir = os.path.expanduser('~/Documents')
                audio_file_path = os.path.join(documents_dir, f"received_audio_{timestamp}.mp3")
                
                # Save audio data to the new file
                with open(audio_file_path, "wb") as f:
                    f.write(audio_data)
   
                # Stop the currently playing audio if any
                sound.stop_all_effects()
                
                # Play the new audio file
                sound.play_effect(audio_file_path)
            
            conn.close()  # 确保连接关闭
            time.sleep(0.1)  # 给一点时间让连接完全关闭

class MyScene(Scene):
    def setup(self):
        self.background_color = 'black'

    def draw(self):
        # Font configuration
        font_name = 'Helvetica'
        font_size = 120
        # Create a text image
        text_img, sz = render_text(text_to_display, font_name, font_size)
        # Calculate the position to center the text
        x = (self.size.w - sz.w) / 2
        y = (self.size.h - sz.h) / 2
        # Draw the text image at the center of the screen
        image(text_img, x, y)
            
    def touch_began(self, touch):
        self.view.close()
        # Clean up all audio files when the scene is closed
        documents_dir = os.path.expanduser('~/Documents')
        for filename in os.listdir(documents_dir):
            if filename.startswith("received_audio_"):
                file_path = os.path.join(documents_dir, filename)
                os.remove(file_path)

receive_thread = threading.Thread(target=receive_data)
receive_thread.daemon = True
receive_thread.start()

run(MyScene(), orientation=LANDSCAPE, frame_interval=1, show_fps=False)