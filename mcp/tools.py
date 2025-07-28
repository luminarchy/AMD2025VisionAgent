from fastmcp import FastMCP, Context
from sam2.sam2_image_predictor import SAM2ImagePredictor
import torch
import logging
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine
from functools import partial
import image as im
import numpy as np
import skimage
import os

logger = logging.getLogger(__name__)

dbname = os.environ['DB_NAME']
dbfile = os.environ['DB_FILE']
dbid = int(os.environ['DB_ID'])
numcols = int(os.environ['NUM_COLS'])
count = 0
colortype = {"protanopia": 0, "deuteranopia": 1, "tritanopia": 2, "achromatopsia": 3}

async def initialize_tools(mcp: FastMCP):
    predictor = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-large")
    logger.info("setup started")
    register_select(mcp, predictor)
    logger.info("setup ended")

def register_select(mcp, predictor):

    @mcp.tool()
    async def segment(file: str): 
        """
        Retrieves information in the database by searching using the value of one parameter
        parameter: the parameter to filter into (the column name in the database). 
        value: the value to filter the search by. 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        f = open(file)
        img = f.read()
        img = im.conv64toarray(img)
        with torch.inference_mode(), torch.autocast(device_type='cuda', dtype=torch.bfloat16):
            predictor.set_image(img)

    
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

        f = open(file)
        img = f.read()
        img = im.conv64toarray(img)
        img = np.uint8(np.dot(img, correction) * 255)
    
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
        f = open(file)
        img = f.read()
        img = im.conv64toarray(img)
        
        imglms = np.dot(img[:,:,:3], im.lms())
        imglms = np.uint8(np.dot(img, matrix))
        imgrgb = np.uint8(np.dot(imglms, im.rgb()) * 255)

        
    
    
    
            

def register_insert(mcp, engine, parameters):
    @mcp.tool()
    async def put_entry(values: dict, ctx: Context): 
        """Inserts a singular entry into the databaseHome
        Questions
        AI Assist
        Labs
        Tags
        
            values: dictionary with the values of the entry to be entered in the database with keys corresponding to parameter names
            """
        
        async with engine.connect() as conn, conn.begin():
            df = {}
            # sql = f"INSERT INTO {dbname} VALUES("
            for p in range(1, len(parameters)):
                df[parameters[p]] = [values.get(parameters[p], None)]
                

            #     sql += f"'{values.get(parameters[p], None)}'"
            #     if p != len(parameters) - 1:
            #         sql += ", "
            # sql += ")"

            # if dbid != -1:
            #     sql += f" ON CONFLICT({parameters[dbid]}) DO (UPDATE {dbname} SET "
            #     for p in range(len(parameters)):
            #         sql += f"{parameters[p]} = {values.get(parameters[p], None)}"
            #         if p != len(parameters) - 1:
            #             sql += ", "
            #     sql += f" WHERE {parameters[dbid]} = {values.get(parameters[dbid])}"
            # logger.info(f"generated sql query: {sql}")
            logger.info(f"dict: {df}")
            global count
            df = pd.DataFrame(df, index = [count + 1])
            df.index.name = "id"
            logger.info(f"Inserting data: \n {df}")
            try:
                slq = lambda x: df.to_sql(dbname, x, if_exists = 'append')
                await conn.run_sync(slq)
                logger.info(f"sucessfully inserting into db")
                return "Successfully updated database"
            except Exception as e:
                logger.exception(f"Database insert error: {e}")
                return "Error updating database"
                

            
        

