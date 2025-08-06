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
        # Open the images file
        f = open("images/" + file + ".txt")
        img = f.read()
        img = im.conv64toim(img) # convert to RGB PIL imgae
        img = img.convert("RGB")
        
        # Setup segmentation model
        inputs = image_processor(images=[img], return_tensors="pt")
        with torch.no_grad(), torch.autocast(device_type='cuda', dtype= float):
            outputs = model(**inputs) # Get outputs
        results = image_processor.post_process_object_detection(
            outputs, 
            target_sizes=torch.tensor([img.size[::-1]]),
            threshold=threshold,
        ) 
        output = []
        for result in results: # Format each result
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
        f = open("images/" + file + ".txt") #read image into np array
        img = f.read()
        img = im.conv64toarray(img)
        
        for value in boxes: # draw bounding boxes
            rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) # random coloring
            img = cv2.rectangle(img, (value[1][1][0], value[1][1][1]), (value[1][1][2], value[1][1][3]), rgb, 1)
            cv2.putText(img, f"{value[0]}: {value[1][0]}", (value[1][1][0], value[1][1][1]), cv2.FONT_HERSHEY_PLAIN, 1, rgb, 2)
        PILimg = Image.fromarray(np.uint8(im)).convert('RGB') # convert to PIL image
        save = "images/segment" + file + ".jpg" # save as new file
        cv2.imwrite(save, img) 
        return f"The color corrected image file name is corected{file}"
        #return f"![image](data:image/jpeg;base64,{im.encode_image(PILimg)})"
    
    @mcp.tool()
    async def get_specific_segment(file: str, boxes: list, label: str, ctx: Context, idx: int = 0) -> ImageContent:
        """
        Retrieves a segment of the image and saves it as a file. 
        file: the image that has been segmented. Can be retrieved through conversation history
        boxes: the bounding boxes, labels, and scores of the segmented image. Formatted the same as the output of the tool 'segment'. i.e.: [(label, [score, [box]]), ...]
        label: the label of the segment to retrieve
        idx: (optional default = 0) if there are multiple segments with the same label, the index of the specific segment to retrieve
        returns the image cropped to the region of the segment
        """
        f = open("images/" + file + ".txt") # open image as np.array
        img = f.read()
        img = im.conv64toarray(img)

        # Get the boxes with corresponding label
        indices = [i for i, val in enumerate(boxes) if val[0] == label]
        if len(indices) == 0: # if no boxes are found
            logger.info(f"item not found. Ensure that label input is correct. Bounding boxes: {boxes}. All possible labels: {classes_map}")
            return f"item not found. Ensure that label input is correct. Bounding boxes: {boxes}. All possible labels: {classes_map}"
        if len(indices) == 1: # if there is only one box
            img = img[indices[0][1][1][1]:indices[0][1][1][3], indices[0][1][1][0]:indices[0][1][1][2], :]
            PILimg = Image.fromarray(np.uint8(img)).convert('RGB')
            return im.encode_image(PILimg)
        else: # if there are multiple boxes
            if idx >= len(indices): # if provided index is greater than number of boxes
                logger.info(f"index out of bounds. There are {len(indices)} total segments for {label}")
                return f"index out of bounds. There are {len(indices)} total segments for {label}"
            # get box at index 
            img = img[indices[idx][1][1][1]:indices[idx][1][1][3], indices[idx][1][1][0]:indices[idx][1][1][2], :]
            PILimg = Image.fromarray(np.uint8(img)).convert('RGB') 
            #return f"The color corrected image file name is corected{file}"
            return f"![image](data:image/jpeg;base64,{im.encode_image(PILimg)})"
    
    @mcp.tool()
    async def correct(file: str, dp: float = 1, dd: float = 1) -> str: 
        """
        Applies a color-correcting filter onto a given image for colorblind vision
        file: the inputted image
        dp: (default 1) the degree of protanopia colorblindness
        dd: (default 1) the degree of deuteranopia colorblindness
        returns the color-corrected image in accepted format
        """
        correction = np.array([[1 - dd/2, dd/2, 0],
                         [dp/2, 1 - dd, 1-dp/2 * dd],
                         [dp/4, dd/4, 1 - (dp + dd)/4]]).T # correction matrix
        
        # open file
        f = open("images/" + file + ".txt") 
        img = f.read() # read image
        img = im.conv64toarray(img)
        img = np.uint8(np.dot(img, correction) * 255) # apply correction
        PILimg = Image.fromarray(np.uint8(img)).convert('RGB')
        
        save = "images/corrected" + file + ".jpg" # save file
        cv2.imwrite(save, img)
        logger.info(f"Image stored at /images/corected{file}.jpg")
        #return f"The color corrected image file name is corected{file}"
        #data:image/jpeg;base64,{im.encode_image(PILimg)}
        return f"![image](http://localhost:8004/corrected{file}.jpg)"
    

        
    
    @mcp.tool()
    async def simulate(file: str, color: str, degree: float):
        """
        Simulats an image in colorblind vision. 
        file: the inputted imgae
        color: the type of colorblindness
        degree: the degree of colorblindness
        """
        matrix = []
        match color: # get colorblindness matrix
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
        f = open("images/" + file + ".txt") # open file
        img = f.read()
        img = im.conv64toarray(img)
        
        imglms = np.dot(img[:,:,:3], im.lms()) # convert to lms colorspace
        imglms = np.uint8(np.dot(img, matrix)) # apply filter
        imgrgb = np.uint8(np.dot(imglms, im.rgb()) * 255) # convert back to RGB
        PILimg = Image.fromarray(np.uint8(imgrgb)).convert('RGB')
        cv2.imwrite("images/simulated_" + file + ".jpg", imgrgb) # save image
        logger.info(f"Image stored at /app/backend/data/images/simulated_{file}.jpg")
        return f"The color corrected image file name is corected{file}"
        #return f"![image](data:image/jpeg;base64,{im.encode_image(PILimg)})"