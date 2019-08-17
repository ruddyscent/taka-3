#!/usr/bin/env python

# steore.py: depth analysis on Jetson TX2.
# Kyungwon Chun <kwchun@biobrain.kr>

import cv2
import numpy as np

STATION = 'udp://192.168.0.178:9999?overrun_nonfatal=1&fifo_size=1316'
STEREO_SIZE = (640, 360)
MONOCULAR = (STEREO_SIZE[0] / 2, STEREO_SIZE[1])
MODEL_INPUT = (513, 257)

cap = cv2.VideoCapture(STATION, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print('VideoCapture not opened')
    exit(-1)

while True:
    ret, frame = cap.read()

    if not ret:
        print('frame empty')
        break

    left = frame[:, :MONOCULAR[0]]
    right = frame[:, MONOCULAR[0]:]

    left = cv2.resize(left, MODEL_INPUT, interpolation = cv2.INTER_LANCZOS4)
    right = cv2.resize(right, MODEL_INPUT, interpolation = cv2.INTER_LANCZOS4)

    cv2.imshow('left', left)
    cv2.imshow('right', right)

    # Convert to RGB and then CHW.
    left = np.transpose(left[:, :, ::-1], [2, 0, 1]).astype(np.float16)
    left /= 255.0

    right = np.transpose(right[:, :, ::-1], [2, 0, 1]).astype(np.float16)
    right /= 255.0
    
    with open('left.bin', 'wb') as w:
        left.reshape(-1).tofile(w)

    with open('right.bin', 'wb') as w:
        right.reshape(-1).tofile(w)
    
    if cv2.waitKey(1)&0XFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
