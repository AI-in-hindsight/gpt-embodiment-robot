import sounddevice as sd
import numpy as np
import wave
from openai import OpenAI
import json
import socket
import pygame
import struct
import time

# 初始化OpenAI客户端
OPEN_API_KEY = 'your_key' #  改为你的OpenAI API key
client = OpenAI(api_key=OPEN_API_KEY)

def record_audio(duration=5, filename="output.wav", samplerate=16000):
    """Records audio for a specified duration and saves it as a WAV file."""
    print("Recording...")
    audio_data = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording stopped.")
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(audio_data.tobytes())
    print(f"Audio saved to {filename}")

def speech_to_text(api_key, file_path):
    client = OpenAI(api_key=api_key)
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return response.text

def send_to_iphone(kaomoji, audio_file, host='192.168.101.10', port=12345): #  改为你的手机IP地址
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            kaomoji_data = kaomoji.encode()
            kaomoji_len = len(kaomoji_data)
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            audio_len = len(audio_data)
            data = struct.pack(f'!I{kaomoji_len}sI{audio_len}s', kaomoji_len, kaomoji_data, audio_len, audio_data)
            s.sendall(data)
    except Exception as e:
        print("Connection to iPhone failed. Please check the IP address and port number.", e)

def play_audio(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.delay(100)
    pygame.mixer.quit()

def main():
    while True:
        # Record user's speech
        record_audio(duration=5, filename="user_input.wav", samplerate=16000) #  录音不能自动停止，所以设置了固定的录音时长5秒，可以修改
        
        # Convert speech to text
        user_text = speech_to_text(OPEN_API_KEY, "user_input.wav")
        print("You said:", user_text)
        
        # Process text to generate response
        if user_text.lower().strip() == "quit":
            break
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125", # 可以改成其他版本
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "假设你是一个可以和人类对话的具身机器人,你的设定是我的男友，爱吃醋，很霸道，喜欢策划惊喜，反应内容包括响应内容,以及对应的kaomoji表情和头部动作(双轴舵机转动参数)。以json格式返回，响应内容定义为response，表情定义为kaomoji，kaomoji表情要反映响应内容情感。与表情对应的头部动作水平角度（无需单位）为servoX，范围是10~170，面向正前方是90。与表情对应的头部动作垂直角度（无需单位）为servoY，范围是10~170，水平面是90。"},
                {"role": "user", "content": user_text},
            ]
        )
        result = json.loads(response.choices[0].message.content)
        print(response.choices[0].message.content)

        # Convert text to speech and send data
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx", #  机器人的音色，可以参考OPENAI API DOCS修改
            input=result['response'],
        )
        speech_response.stream_to_file("output.mp3")
        send_to_iphone(result['kaomoji'], "output.mp3")

        # Wait for 5 seconds before starting a new recording
        time.sleep(8) #  为了避免程序过快进入录音，而造成把机器人的回复录下来的情况，这里设置了每次发送完回复要等8秒，可修改


if __name__ == "__main__":
    main()
