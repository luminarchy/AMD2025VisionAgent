from fastmcp import FastMCP, Context
import logging
import image as im
import numpy as np
import os
import requests
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
import torch
from PIL import Image
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
        Retrieves information in the database by searching using the value of one parameter
        parameter: the parameter to filter into (the column name in the database). 
        value: the value to filter the search by. 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        f = open("/images/" + file)
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
    async def correct(file: str, color: str, dp: float, dd: float): 
        """
        Retrieves information in the database by searching using the values of multiple parameters. 
        parameter: the parameters to filter into (the column name in the database). 
        value: the values to filter the search by. Sorted by the corresponding parameter value in parameter. Indicies should match up for parameter and value. 
        all: (default True) whether or not all parameters must match their corresponding value. If true, uses AND to find entries that match all constraints. If false, uses OR to find entries that match at least one constraint. 
        limit: (default 10) the max number of entries to be returned 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        correction = np.array([[1 - dp, 2.02344 * dp, -2.52581 * dp],
                         [0.494207 * dd, 1 - dd, 1.24827 * dd],
                         [0, 0, 1]]).T

        f = open("/images/" + file)
        img = f.read()
        img = im.conv64toarray(img)
        img = np.uint8(np.dot(img, correction) * 255)
        save = "corrected" + file
        cv2.imwrite("/imags/corrected_" + file, img)

        
    
    @mcp.tool()
    async def simulate(file: str, color: str, degree: float):
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
        f = open("/images/" + file)
        img = f.read()
        img = im.conv64toarray(img)
        
        imglms = np.dot(img[:,:,:3], im.lms())
        imglms = np.uint8(np.dot(img, matrix))
        imgrgb = np.uint8(np.dot(imglms, im.rgb()) * 255)
        cv2.imwrite("/imags/simulated_" + file, imgrgb)