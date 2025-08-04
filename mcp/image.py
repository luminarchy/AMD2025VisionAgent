import numpy as np
import io
import base64
import logging
from PIL import Image
from fastmcp.utilities.types import Image as Img
from mcp.types import ImageContent
import cv2

def conv64toim(b64: str):
    """
    Convert a base64 image string to PIL image
    b64: base64 image string
    returns a PIL image
    """
    image_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(image_bytes))
    return img

def conv64toarray(b64: str):
    """
    Convert a base64 image string to numpy array
    b64: base64 image string
    returns a numpy array
    """
    img = conv64toim(b64)
    a = np.asarray(img)
    return a/255.0

def encode_image(image):
    """
    Convert a PIL image to a base64 strng
    image: PIL image
    returns a base64 string
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
    # img_bytes = buffer.getvalue()
    # img_obj = Img(data=img_bytes, format="png")
    # return img_obj.to_image_content()

def protanopia(degree: float):
    """
    Gets the matrix for protanopia colorblindness
    degree: degree of colorblindness
    returns: a 3x3 matrix
    """
    return np.array([[1 - degree, 2.02344 * degree, -2.52581 * degree],
                         [0, 1, 0],
                         [0, 0, 1]]).T
def deuteranopia(degree: float):
    """
    Gets the matrix for deuteranopia colorblindness
    degree: degree of colorblindness
    returns: a 3x3 matrix
    """
    return np.array([[1, 0, 0],
                         [0.494207 * degree, 1 - degree, 1.24827 * degree],
                         [0, 0, 1]]).T

def tritanopia(degree: float):
    """
    Gets the matrix for tritanopia colorblindness
    degree: degree of colorblindness
    returns: a 3x3 matrix
    """
    return np.array([[1, 0, 0],
                         [0, 1, 0],
                         [-0.395913 * degree, 0.801109 * degree, 1 - degree]]).T

def achromatopsia():
    """
    Gets the matrix for achromatopsia colorblindness
    degree: degree of colorblindness
    returns: a 3x3 matrix
    """
    return np.array([[0.2126, 0.7152, 0.0722], [0.2126, 0.7152, 0.0722], [0.2126, 0.7152, 0.0722]])

def lms():
    """
    Gets the matrix for rgb->lms colorspace conversion
    returns: a 3x3 matrix
    """
    return np.array([[17.8824, 43.5161, 4.11935],
                    [3.45565, 27.1554, 3.86714],
                    [0.0299566, 0.184309, 1.46709]]).T

def rgb():
    """
    Gets the matrix for lms->rgb colorspace conversion
    returns: a 3x3 matrix
    """
    return np.array([[0.0809, -0.1305, 0.1167],
                    [-0.0102, 0.0540, -0.1136],
                    [-0.0004, -0.0041, 0.6935]]).T


