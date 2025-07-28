import numpy as np
import io
import base64
import logging
from PIL import Image
import cv2

def conv64toim(b64: str):
    image_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(image_bytes))
    return img

def conv64toarray(b64: str):
    img = conv64toim(b64)
    a = np.asarray(img)
    return a/255.0

def protanopia(degree: float):
    return np.array([[1 - degree, 2.02344 * degree, -2.52581 * degree],
                         [0, 1, 0],
                         [0, 0, 1]]).T
def deuteranopia(degree: float):
    return np.array([[1, 0, 0],
                         [0.494207 * degree, 1 - degree, 1.24827 * degree],
                         [0, 0, 1]]).T

def tritanopia(degree: float):
    return np.array([[1, 0, 0],
                         [0, 1, 0],
                         [-0.395913 * degree, 0.801109 * degree, 1 - degree]]).T

def achromatopsia():
    return np.array([[0.2126, 0.7152, 0.0722], [0.2126, 0.7152, 0.0722], [0.2126, 0.7152, 0.0722]])

def lms():
    return np.array([[17.8824, 43.5161, 4.11935],
                    [3.45565, 27.1554, 3.86714],
                    [0.0299566, 0.184309, 1.46709]]).T

def rgb():
    return np.array([[0.0809, -0.1305, 0.1167],
                    [-0.0102, 0.0540, -0.1136],
                    [-0.0004, -0.0041, 0.6935]]).T


