from fastmcp import FastMCP, Context
import logging
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine
from functools import partial
import format as f
import os

logger = logging.getLogger(__name__)

dbname = os.environ['DB_NAME']
dbfile = os.environ['DB_FILE']
dbid = int(os.environ['DB_ID'])
numcols = int(os.environ['NUM_COLS'])
count = 0

def read_sql_query(con, stmt):
    return pd.read_sql_query(stmt, con)

async def initialize_tools(mcp: FastMCP):
    logger.info("setup started")
    rep = lambda x: str(x).replace("_x000D_", "").strip()
    convert = {}
    for i in range(numcols):
        convert[i] = rep
    pf = pd.read_excel(dbfile, header = 0, index_col = 0, converters = convert)
    pf.index.name = 'id'
    engine = create_async_engine('sqlite+aiosqlite:///./test.db', echo=False)
    parameters = ["id"]
    parameters.extend(pf.columns.tolist())
    global count 
    count += len(pf)
    logger.info(f"Database parameters: {parameters}")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(partial(pf.to_sql, dbname))
    register_select(mcp, engine, parameters)
    register_insert(mcp, engine, parameters)
    logger.info("setup ended")

def register_select(mcp, engine, parameters):

    @mcp.tool()
    async def get_one_parameter(parameter: str, value: str, ctx: Context, limit: int = 10): 
        """
        Retrieves information in the database by searching using the value of one parameter
        parameter: the parameter to filter into (the column name in the database). 
        value: the value to filter the search by. 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        async with engine.connect() as conn, conn.begin():
            if parameter not in parameters:
                return f"Search parameter {parameter} does not match database column names. Please reformat query values and try again. Accepted parameter values: {parameters}"
            try:
                sql = f"SELECT * FROM {dbname} WHERE {parameter} LIKE \"%{value}%\" LIMIT {limit}"
                result = await conn.run_sync(partial(pd.read_sql_query, sql))
                logger.info(f"successfully executing sql query: {result}")
                if result.shape[0] == 0:
                    logger.exception(f"database invalid value, {value}, in parameter, {parameter}.")
                    return f"database invalid value, {value}, in parameter, {parameter}. Please check spelling and try again with a different value."
                else:
                    # ctx.info(f"User requested author {authors["Poet"][0]} under input: {author_first} {author_last}")
                    # ctx.info(f"Related tags for {authors["Poet"][0]}: {f.format_tags(f.format_list(authors["Tags"]))}")
                    return f.format_entries(result, parameters)
            except Exception as e:
                logger.exception(f"Database query error: {e}")
                return "Error searching database"

    
    @mcp.tool()
    async def get_multiple_parameters(parameter: list[str], value: list[str], ctx: Context, al: bool = True, limit: int = 10): 
        """
        Retrieves information in the database by searching using the values of multiple parameters. 
        parameter: the parameters to filter into (the column name in the database). 
        value: the values to filter the search by. Sorted by the corresponding parameter value in parameter. Indicies should match up for parameter and value. 
        all: (default True) whether or not all parameters must match their corresponding value. If true, uses AND to find entries that match all constraints. If false, uses OR to find entries that match at least one constraint. 
        limit: (default 10) the max number of entries to be returned 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        async with engine.connect() as conn, conn.begin():
            op = "AND "
            if not al: 
                op = "OR "
            sql = f"SELECT * FROM {dbname} WHERE "
            for x in range(len(parameter)):
                
                if parameter[x] not in parameters:
                    return f"Search parameter {parameter[x]} does not match database column names. Please reformat query values and try again. Accepted parameter values: {parameters}"
                if x != 0:
                    sql += op
                sql += f"{parameter[x]} LIKE \"%{value[x]}%\""
            sql += f" LIMIT {limit}"
            logger.info(f"generated sql query: {sql}")
            try:
                result = await conn.run_sync(partial(pd.read_sql_query, sql))
                logger.info(f"successfully executing sql query: {result}")
                if result.shape[0] == 0:
                    logger.exception(f"database invalid values, {value}, in parameters, {parameter}.")
                    return f"database invalid values, {value}, in parameters, {parameter}. Please check spelling and try again with a different value."
                else:
                    # ctx.info(f"User requested author {authors["Poet"][0]} under input: {author_first} {author_last}")
                    # ctx.info(f"Related tags for {authors["Poet"][0]}: {f.format_tags(f.format_list(authors["Tags"]))}")
                    return f.format_entries(result, parameters)
            except Exception as e:
                logger.exception(f"Database query error: {e}")
                return "Error searching database"
        
    @mcp.tool()
    async def get_one_parameter_mult(parameter: str, value: list[str], ctx: Context, al:bool = True, limit: int = 10): 
        """
        Retrieves information in the database by searching using the value of one parameter using multiple values. 
        parameter: the parameter to filter into (the column name in the database). 
        value: the values to filter the search by. 
        all: (default True) whether or not all parameters must match their corresponding value. If true, uses AND to find entries that match all constraints. If false, uses OR to find entries that match at least one constraint. 
        limit: (default 10) the max number of entries to be returned 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        if parameter not in parameters:
            return f"Search parameter {parameter} does not match database column names. Please reformat query values and try again. Accepted parameter values: {parameters}"
        async with engine.connect() as conn, conn.begin():
            op = "AND "
            if not al: 
                op = "OR "
            sql = f"SELECT * FROM {dbname} WHERE "
            for x in range(len(value)):
                if x != 0:
                    sql += op
                sql += f"{parameter} LIKE \"%{value[x]}%\""
            sql += f" LIMIT {limit}"
            logger.info(f"generated sql query: {sql}")
            try:
                result = await conn.run_sync(partial(pd.read_sql_query, sql))
                logger.info(f"successfully executing sql query: {result}")
                if result.shape[0] == 0:
                    logger.exception(f"database invalid values, {value}, in parameter, {parameter}.")
                    return f"database invalid values, {value}, in parameter, {parameter}. Please check spelling and try again with a different value."
                else:
                    # ctx.info(f"User requested author {authors["Poet"][0]} under input: {author_first} {author_last}")
                    # ctx.info(f"Related tags for {authors["Poet"][0]}: {f.format_tags(f.format_list(authors["Tags"]))}")
                    return f.format_entries(result, parameters)
            except Exception as e:
                logger.exception(f"Database query error: {e}")
                return "Error searching database"
    
    @mcp.tool()
    async def get_mult_parameter_mult(parameter: list[str], value: list[list[str]], ctx: Context, al: bool = True, limit: int = 10): 
        """
        Retrieves information in the database by searching using the value of multiple parameters using multiple values. 
        parameter: the parameter to filter into (the column name in the database). 
        value: the values to filter the search by. 
        all: (default True) whether or not all parameters must match their corresponding value. If true, uses AND to find entries that match all constraints. If false, uses OR to find entries that match at least one constraint. 
        limit: (default 10) the max number of entries to be returned 
        returns: all entries in the database that have <value> in their <parameter> column. 
        """
        async with engine.connect() as conn, conn.begin():
            op = "AND "
            if not al: 
                op = "OR "
            sql = f"SELECT * FROM {dbname} WHERE "
            for x in range(len(parameter)):
                if parameter[x] not in parameters:
                    return f"Search parameter {parameter[x]} does not match database column names. Please reformat query values and try again. Accepted parameter values: {parameters}"
                for y in range(len(value)):
                    if x+y != 0:
                        sql += op
                    sql += f"{parameter[x]} LIKE \"%{value[x][y]}%\""
            sql += f" LIMIT {limit}"
            logger.info(f"generated sql query: {sql}")
            try:
                result = await conn.run_sync(partial(pd.read_sql_query, sql))
                logger.info(f"successfully executing sql query: {result}")
                if result.shape[0] == 0:
                    logger.exception(f"database invalid values, {value}, in parameters, {parameter}.")
                    return f"database invalid values, {value}, in parameters, {parameter}. Please check spelling and try again with a different value."
                else:
                    # ctx.info(f"User requested author {authors["Poet"][0]} under input: {author_first} {author_last}")
                    # ctx.info(f"Related tags for {authors["Poet"][0]}: {f.format_tags(f.format_list(authors["Tags"]))}")
                    return f.format_entries(result, parameters)
            except Exception as e:
                logger.exception(f"Database query error: {e}")
                return "Error searching database"
            

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
                

            
        

