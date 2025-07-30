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
import random

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
        returns the segments found including their labels, scores, and box coordinates in the format of [(label, [score, [box]])...]
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
        output = []
        for result in results:
            for score, label_id, box in zip(
                result["scores"], result["labels"], result["boxes"]
            ):
                score = round(score.item(), 2)
                label = classes_map[label_id.item()]
                box = [round(i, 2) for i in box.tolist()]
                output.append([label, (score, box)])
        return output
        
    @mcp.tool()
    async def show_segments(file: str, boxes: list, ctx: Context) -> ImageContent:
        """
        Plots the segments and labels on the input image. 
        file: the image that has been segmented. Can be retrieved through conversation history
        boxes: the bounding boxes, labels, and scores. Formatted the same as the output of the tool 'segment'. i.e.: [(label, [score, [box]]), ...]
        returns an image with the boxes drawn designating segments 
        """
        im = Image.open(file)
        im = np.array(im)
        print(im.shape)
        for value in boxes:
            rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            im = cv2.rectangle(im, (value[1][1][0], value[1][1][1]), (value[1][1][2], value[1][1][3]), rgb, 1)
            cv2.putText(im, f"{value[0]}: {value[1][0]}", (value[1][1][0], value[1][1][1]), cv2.FONT_HERSHEY_PLAIN, 1, rgb, 2)
        PILimg = Image.fromarray(np.uint8(im)).convert('RGB')
        save = "images/segment" + file + ".jpg"
        cv2.imwrite(save, im)
        return im.encode_image(PILimg)
    
    @mcp.tool()
    async def get_segment(file: str, boxes: list, label: str, ctx: Context, idx: int = 0) -> ImageContent:
        """
        Retrieves a segment of the image and saves it as a file. 
        file: the image that has been segmented. Can be retrieved through conversation history
        boxes: the bounding boxes, labels, and scores of the segmented image. Formatted the same as the output of the tool 'segment'. i.e.: [(label, [score, [box]]), ...]
        label: the label of the segment to retrieve
        idx: (optional default = 0) if there are multiple segments with the same label, the index of the specific segment to retrieve
        returns the image cropped to the region of the segment
        """
        im = Image.open(file)
        im = np.array(im)
        indices = [i for i, val in enumerate(boxes) if val[0] == label]
        if len(indices) == 0:
            logger.info(f"item not found. Ensure that label input is correct. Bounding boxes: {boxes}. All possible labels: {classes_map}")
            return f"item not found. Ensure that label input is correct. Bounding boxes: {boxes}. All possible labels: {classes_map}"
        if len(indices) == 1:
            im = im[indices[0][1][1][1]:indices[0][1][1][3], indices[0][1][1][0]:indices[0][1][1][2], :]
            PILimg = Image.fromarray(np.uint8(im)).convert('RGB')
            return im.encode_image(PILimg)
        else:
            im = im[indices[idx][1][1][1]:indices[idx][1][1][3], indices[idx][1][1][0]:indices[idx][1][1][2], :]
            PILimg = Image.fromarray(np.uint8(im)).convert('RGB')
            return im.encode_image(PILimg)
    
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