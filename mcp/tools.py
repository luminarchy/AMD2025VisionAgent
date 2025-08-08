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
boxdict = {}


async def initialize_tools(mcp: FastMCP):
    logger.info("setup started")
    register_select(mcp)
    logger.info("setup ended")


def register_select(mcp):

    @mcp.tool()
    async def segment(file: str): 
        """ Segments the image into layout categories.
        Args:
            file: the image to be segmented
        returns the segments found including their labels, scores, and box coordinates in the format of [(label, [score, [box]])...]
        """
        # Open the images file
        try:
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
                    box = [round(i) for i in box.tolist()]
                    output.append([label, (score, box)])
            global boxdict
            boxdict[file] = output
            return f"The following segments were found {[val[0] for val in output]}"
        except Exception as e:
            logger.info(f"Segmentation error: {e}")
            return f"Segmentation error: {e}"
        
    @mcp.tool()
    async def visualize_segmentaton(ctx: Context, file: str = "") -> ImageContent:
        """ Visualizes a segmented image by drawing bounding boxes onto the image
        Args:
            file (string): the image that has been segmented. If not provided, this should be the last inputted image in the conversation history. 
        returns an image with the boxes drawn designs
        """
        try:
            boxes = boxdict.get(file, None)
            if boxes == None:
                return("No segments found. Use the segment tool function first to find the segments for the image.")
            if file == "": 
                return("Please specify which file to use")
            f = open("images/" + file + ".txt") #read image into np array
            img = f.read()
            img = im.conv64toarray(img)
            
            for value in boxes: # draw bounding boxes
                rgb = (random.randint(0, 1), random.randint(0, 1), random.randint(0, 1)) # random coloring
                img = cv2.rectangle(img, (value[1][1][0], value[1][1][1]), (value[1][1][2], value[1][1][3]), rgb, 1)
                cv2.putText(img, f"{value[0]}: {value[1][0]}", (value[1][1][0], value[1][1][1]), cv2.FONT_HERSHEY_PLAIN, 1, rgb, 2)
            #PILimg = Image.fromarray(np.uint8(img)).convert('RGB') # convert to PIL image
            save = "images/segment" + file + ".jpg" # save as new file
            img = cv2.cvtColor(np.uint8(img *255), cv2.COLOR_RGB2BGR)
            cv2.imwrite(save, img) 
            return f"![image](http://localhost:8004/segment{file}.jpg)"
            #return f"![image](data:image/jpeg;base64,{im.encode_image(PILimg)})"
        except Exception as e:
            logger.info(f"visualize segment error: {e}")
            return f"Visualize segmentation error: {e}"
    
    @mcp.tool()
    async def get_specific_segment(label: str, ctx: Context, file: str = "", idx: int = 0) -> ImageContent:
        """ Retrieves a segment of the image and saves it as a file. 
        Args:
            file (string): the image that has been segmented. Must have first called segment(). Can be retrieved through conversation history
            label (string): the label of the segment to retrieve
            idx: (optional default = 0) if there are multiple segments with the same label, the index of the specific segment to retrieve
        returns the image cropped to the region of the segment
        """
        boxes = boxdict.get(file, None)
        if boxes == None:
            return("No segments found. Use the segment tool function first to find the segments for the image.")
        if file == "": 
            return("Please specify which file to use")
        lab = label.lower().strip()
        try: 
            f = open("images/" + file + ".txt") # open image as np.array
            img = f.read()
            img = np.uint8(im.conv64toarray(img)*255)
    
            # Get the boxes with corresponding label
            indices = [i for i, val in enumerate(boxes) if val[0].lower() == lab]
            if len(indices) == 0: # if no boxes are found
                logger.info(f"item not found. Ensure that label input is correct. Bounding boxes: {boxes}. All possible labels: {classes_map}")
                return f"item not found. Ensure that label input is correct. Bounding boxes: {boxes}. All possible labels: {classes_map}"
            elif len(indices) == 1: # if there is only one box
                i = indices[0]
                img = img[boxes[i][1][1][1]:boxes[i][1][1][3], boxes[i][1][1][0]:boxes[i][1][1][2], :]
            else: # if there are multiple boxes
                if idx >= len(indices): # if provided index is greater than number of boxes
                    logger.info(f"index out of bounds. There are {len(indices)} total segments for {label}")
                    return f"index out of bounds. There are {len(indices)} total segments for {label}"
                # get box at index 
                i = indices[idx]
                img = img[boxes[i][1][1][1]:boxes[i][1][1][3], boxes[i][1][1][0]:boxes[i][1][1][2], :]
                #PILimg = Image.fromarray(np.uint8(img)).convert('RGB') 
                #return f"The color corrected image file name is corected{file}"
            save = "images/" + lab + file + ".jpg" # save as new file
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(save, img) 
            return f"![image](http://localhost:8004/{lab}{file}.jpg)"
        except Exception as e:
            logger.info(f"get specific segment error: {e}")
            return f"get specific segment error: {e}"
    
    @mcp.tool()
    async def correct(file: str, dp: float = 1, dd: float = 1) -> str: 
        """ Applies a color-correcting filter onto a given image for colorblind vision
        Args:
            file (string): the inputted image
            dp (int): (default 1) the degree of protanopia colorblindness
            dd (int): (default 1) the degree of deuteranopia colorblindness
        Returns:
            the color-corrected image in markdown format
        """
        correction = np.array([[1 - dd/2, dd/2, 0],
                         [dp/2, 1 - dd, 1-dp/2 * dd],
                         [dp/4, dd/4, 1 - (dp + dd)/4]]).T # correction matrix
        
        # open file
        try:
            f = open("images/" + file + ".txt") 
            img = f.read() # read image
            img = im.conv64toarray(img)
            img = np.uint8(np.dot(img, correction) * 255) # apply correction
            PILimg = Image.fromarray(np.uint8(img)).convert('RGB')
            
            save = "images/corrected" + file + ".jpg" # save file
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(save, img)
            logger.info(f"Image stored at /images/corected{file}.jpg")
            #return f"The color corrected image file name is corected{file}"
            #data:image/jpeg;base64,{im.encode_image(PILimg)}
            return f"![image](http://localhost:8004/corrected{file}.jpg)"
        except Exception as e:
            logger.info(f"Image correct error: {e}")
            return f"Image correct error: {e}"
    

        
    
    @mcp.tool()
    async def simulate(file: str, color: str, degree: float):
        """ Simulates an image in colorblind vision. 
        Args:
            file (string): the inputted imgae
            color (string) : the type of colorblindness
            degree (string) : the degree of colorblindness
        Returns:
            The markdown image simulated in colorblind vision
        """
        matrix = []
        match color: # get colorblindness matrix
            case "protanopia":
                matrix = im.protanopia(degree)
            case "deuteranopia":
                matrix = im.deuteranopia(degree)
            case "tritanopia":
                matrix = im.tritanopia(degree)
            case "achromatopsia":
                matrix = im.achromatopsia()
            case __:
                logger.info("color blindness type not found")
        try:
            f = open("images/" + file + ".txt") # open file
            img = f.read()
            img = im.conv64toarray(img)
            
            imglms = np.dot(img[:,:,:3], im.lms()) # convert to lms colorspace
            imglms = np.uint8(np.dot(img, matrix)) # apply filter
            imgrgb = np.uint8(np.dot(imglms, im.rgb()) * 255) # convert back to RGB
            # PILimg = Image.fromarray(np.uint8(imgrgb)).convert('RGB')
            img = cv2.cvtColor(imgrgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite("images/simulated" + file + ".jpg", img) # save image
            logger.info(f"Image stored at /images/simulated{file}.jpg")
            return f"![image](http://localhost:8004/simulated{file}.jpg)"
        except Exception as e: 
            logger.info(f"Image simulate error: {e}")
            return f"Image simulate error: {e}"
        #return f"![image](data:image/jpeg;base64,{im.encode_image(PILimg)})"


    @mcp.tool()
    async def crop(file: str, ctx: Context, top: int = 0, bottom: int = 0, left: int = 0, right: int = 0):
        """ Crops an image. 
        Args: 
            file (string): the inputted image file
            top (int): the number of pixels from the top of the upper bound of the region being cropped (y0) (default 0)
            bottom (int): the number of pixels from the top to the lower bound of the region being cropped (y1) (default 0)
            left (int): the number of pixels from the left to the left bound of the region being cropped  (x0) (default 0)
            right (int): the number of pixels from the left to the right bound of the region being cropped (x1) (default 0)

        Returns:
            string: The image link formatted in markdown containing the image stored in `file` cropped to the region of interest designated by the crop box: (top:bottom, left:right)
        """
        try:
            f = open("images/" + file + ".txt") # open file
            img = f.read()
            img = im.conv64toarray(img)
            img = img[top:bottom, left:right]
            img = cv2.cvtColor(imgrgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite("images/cropped" + file + ".jpg", img) # save image
            logger.info(f"Image stored at /images/cropped{file}.jpg")
            return f"![image](http://localhost:8004/cropped{file}.jpg)"
        except Exception as e:
            logger.info(f"Image crop error: {e}")
            return f"Image crop error: {e}"
                        

@mcp.tool()
async def resize(file: str, ctx: Context, size: tuple[int, int] = (0, 0), scale_x: int = 1, scale_y: int = 1):
    """ Resizes an image. 
        Args: 
            file (string): the inputted image file
            size (tuple): the size (x, y) to resize the image to. If size is (0, 0), then scale factors will be used instead.
            scale_x (int): the scale to horizontally resize the image by. (default 1)
            scale_y (int): the scale to vertically resize the image by. To keep the aspect ratio, this input should be equal to scale_x (default 1)
            
        Returns:
            string: The image link formatted in markdown containing the resized image using bilinear interpolation
        """
    try:
        f = open("images/" + file + ".txt") # open file
        img = f.read()
        img = im.conv64toarray(img)
        if size != (0, 0): # if resizing by size
            img = cv2.resize(img, size)
        else: # if resizing by scale factor
            img = cv2.resize(img, None, fx = scale_x, fy = scale_y, interpolation=cv2.INTER_LINEAR) # bilinear interp
        img = cv2.cvtColor(imgrgb, cv2.COLOR_RGB2BGR) # convert color
        cv2.imwrite("images/resized" + file + ".jpg", img) # save image
        logger.info(f"Image stored at /images/resized{file}.jpg") 
        return f"![image](http://localhost:8004/resized{file}.jpg)"
    except Exception as e:
            logger.info(f"Image crop error: {e}")
            return f"Image crop error: {e}"