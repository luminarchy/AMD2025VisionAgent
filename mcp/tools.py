from fastmcp import FastMCP, Context
import logging
import image as im
import numpy as np
import os
import requests
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
import torch
from PIL import Image
from mcp.types import ImageContent
import cv2

logger = logging.getLogger(__name__)

colortype = {"protanopia": 0, "deuteranopia": 1, "tritanopia": 2, "achromatopsia": 3}
classes_map = {
    0: "Caption",
    1: "Footnote",
    2: "Formula",
    3: "List-item",
    4: "Page-footer",
    5: "Page-header",
    6: "Picture",
    7: "Section-header",
    8: "Table",
    9: "Text",
    10: "Title",
    11: "Document Index",
    12: "Code",
    13: "Checkbox-Selected",
    14: "Checkbox-Unselected",
    15: "Form",
    16: "Key-Value Region",
}
model_name = "ds4sd/docling-layout-heron"
threshold = 0.6
image_processor = RTDetrImageProcessor.from_pretrained(model_name)
model = RTDetrV2ForObjectDetection.from_pretrained(model_name)



async def initialize_tools(mcp: FastMCP):
    logger.info("setup started")
    register_select(mcp)
    logger.info("setup ended")


def register_select(mcp):

    @mcp.tool()
    async def segment(file: str): 
        """
        Segments the document image into layout categories.
        file: the image to be segmented
        """
        f = open("images/" + file + ".txt")
        img = f.read()
        img = im.conv64toim(img)
        img = img.convert("RGB")
        inputs = image_processor(images=[img], return_tensors="pt")
        with torch.no_grad(), torch.autocast(device_type='cuda', dtype= float):
            outputs = model(**inputs)
        results = image_processor.post_process_object_detection(
            outputs,
            target_sizes=torch.tensor([img.size[::-1]]),
            threshold=threshold,
        )
        output = ""
        for result in results:
            for score, label_id, box in zip(
                result["scores"], result["labels"], result["boxes"]
            ):
                score = round(score.item(), 2)
                label = classes_map[label_id.item()]
                box = [round(i, 2) for i in box.tolist()]
                output += (f"{label}:{score} {box} \n")
        return output

    
    @mcp.tool()
    async def correct(file: str, dp: float = 1, dd: float = 1) -> ImageContent: 
        """
        Applies a color-correcting filter onto a given image. 
        file: the inputted image
        dp: (default 1) the degree of protanopia colorblindness
        dd: (default 1) the degree of deuteranopia colorblindness
        """
        correction = np.array([[1 - dp, 2.02344 * dp, -2.52581 * dp],
                         [0.494207 * dd, 1 - dd, 1.24827 * dd],
                         [0, 0, 1]]).T

        f = open("images/" + file + ".txt")
        img = f.read()
        img = im.conv64toarray(img)
        img = np.uint8(np.dot(img, correction) * 255)
        PILimg = Image.fromarray(np.uint8(img)).convert('RGB')
        
        save = "images/corrected" + file + ".jpg"
        cv2.imwrite(save, img)
        logger.info(f"Image stored at /app/backend/data/images/corected_{file}.jpg")
        return im.encode_image(PILimg)

        
    
    @mcp.tool()
    async def simulate(file: str, color: str, degree: float):
        """
        Simulats an image in colorblind vision. 
        file: the inputted imgae
        color: the type of colorblindness
        degree: the degree of colorblindness
        """
        matrix = []
        match color:
            case "protanopia":
                matrix = im.protanopia()
            case "deuteranopia":
                matrix = im.deuteranopia()
            case "tritanopia":
                matrix = im.tritanopia()
            case "achromatopsia":
                matrix = im.achromatopsia()
            case __:
                logger.info("color blindness type not found")
        f = open("images/" + file + ".txt")
        img = f.read()
        img = im.conv64toarray(img)
        
        imglms = np.dot(img[:,:,:3], im.lms())
        imglms = np.uint8(np.dot(img, matrix))
        imgrgb = np.uint8(np.dot(imglms, im.rgb()) * 255)
        PILimg = Image.fromarray(np.uint8(imgrgb)).convert('RGB')
        cv2.imwrite("images/simulated_" + file + ".jpg", imgrgb)
        logger.info(f"Image stored at /app/backend/data/images/simulated_{file}.jpg")
        return im.encode_image(PILimg)