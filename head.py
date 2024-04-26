import cv2
from cvzone.FaceDetectionModule import FaceDetector
import pyfirmata
import numpy as np
import socket
import json
import threading
import time

cap = cv2.VideoCapture(0)
ws, hs = 1280, 720
cap.set(3, ws)
cap.set(4, hs)

if not cap.isOpened():
    print("Camera couldn't Access!!!")
    exit()

port = "/dev/cu.usbmodem70041DD3E6D02"  # 修改为您的 Arduino 的串口地址
board = pyfirmata.Arduino(port)
servo_pinX = board.get_pin('d:9:s')  # pin 9 Arduino
servo_pinY = board.get_pin('d:10:s')  # pin 10 Arduino

detector = FaceDetector()
servoPos = [90, 90]  # initial servo position
last_data_time = 0
running = True  # 控制线程循环的全局变量

def listen_socket():
    global servoPos, last_data_time, running
    s = socket.socket()
    s.bind(('127.0.0.1', 7892))
    s.listen(1)
    while running:
        conn, addr = s.accept()
        data = conn.recv(1024).decode()
        if not data:
            break  # 如果没有数据或者连接被关闭
        print(f"Received data: {data}")
        try:
            jsonData = json.loads(data)
            servoX = jsonData.get('servoX', servoPos[0])
            servoY = jsonData.get('servoY', servoPos[1])
            
            # 限制舵机转动范围
            servoX = max(0, min(180, servoX))
            servoY = max(0, min(180, servoY))
            
            servoPos[0] = servoX
            servoPos[1] = servoY
            
            # 立即控制舵机转动
            servo_pinX.write(servoPos[0])
            servo_pinY.write(servoPos[1])
            
            # 记录接收到数据的时间
            last_data_time = time.time()
            
        except json.JSONDecodeError:
            print("Invalid JSON data received")
        conn.close()
    s.close()

threading.Thread(target=listen_socket, daemon=True).start()

while running:
    success, img = cap.read()
    
    # 如果距离上次接收到数据已经超过1000秒,则进行视觉跟踪
    if time.time() - last_data_time > 1000:
        img, bboxs = detector.findFaces(img, draw=False)

        if bboxs:
            fx, fy = bboxs[0]["center"][0], bboxs[0]["center"][1]
            pos = [fx, fy]
            servoX = np.interp(fx, [0, ws], [180, 0])
            servoY = np.interp(fy, [0, hs], [180, 0])

            # 限制舵机转动范围
            servoX = max(0, min(180, servoX))
            servoY = max(0, min(180, servoY))

            servoPos[0] = servoX
            servoPos[1] = servoY

            cv2.circle(img, (fx, fy), 80, (0, 0, 255), 2)
            cv2.putText(img, str(pos), (fx + 15, fy - 15), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
            cv2.line(img, (0, fy), (ws, fy), (0, 0, 0), 2)  # x line
            cv2.line(img, (fx, hs), (fx, 0), (0, 0, 0), 2)  # y line 
            cv2.circle(img, (fx, fy), 15, (0, 0, 255), cv2.FILLED)
            cv2.putText(img, "TARGET LOCKED", (850, 50), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

        else:
            cv2.putText(img, "NO TARGET", (880, 50), cv2.FONT_HERSHEY_PLAIN, 3, (0, 0, 255), 3)
            cv2.circle(img, (640, 360), 80, (0, 0, 255), 2) 
            cv2.circle(img, (640, 360), 15, (0, 0, 255), cv2.FILLED)
            cv2.line(img, (0, 360), (ws, 360), (0, 0, 0), 2)  # x line
            cv2.line(img, (640, hs), (640, 0), (0, 0, 0), 2)  # y line
            
        servo_pinX.write(servoPos[0])  
        servo_pinY.write(servoPos[1])
        
    else:
        # 如果距离上次接收到数据不足5秒,则显示等待信息
        cv2.putText(img, "Waiting for data...", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
        
    cv2.putText(img, f'Servo X: {int(servoPos[0])} deg', (50, 100), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
    cv2.putText(img, f'Servo Y: {int(servoPos[1])} deg', (50, 150), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord('%'):
        running = False

# 清理资源
cap.release()
cv2.destroyAllWindows
