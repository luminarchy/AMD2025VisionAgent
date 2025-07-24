"""
title: Image convertor
requirements: numpy
"""

from PIL import Image
import numpy as np
from pydantic import BaseModel, Field
from typing import Callable, Awaitable, Any, Optional, Literal
import json
import logging

from open_webui.utils.misc import get_last_user_message_item

def setup_logger():
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.set_name(__name__)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logger()

class Filter:
    class Valves(BaseModel):
        enabled_for_admins: bool = Field(
            default=False,
            description="Whether dynamic vision routing is enabled for admin users.",
        )
        enabled_for_users: bool = Field(
            default=True,
            description="Whether dynamic vision routing is enabled for regular users.",
        )
        pass

    def __init__(self):
        self.valves = self.Valves()
        pass

    async def inlet(
        self,
        body: dict,
        __event_emitter__: Callable[[Any], Awaitable[None]],
        __model__: Optional[dict] = None,
        __user__: Optional[dict] = None,
    ) -> dict:
        if __user__ is not None:
            if __user__.get("role") == "admin" and not self.valves.enabled_for_admins:
                return body
            elif __user__.get("role") == "user" and not self.valves.enabled_for_users:
                return body

        messages = body.get("messages")
        if messages is None:
            # Handle the case where messages is None
            return body
        logger.info("getting messages")
        user_message = get_last_user_message_item(messages)
        if user_message is None:
            # Handle the case where user_message is None
            return body
        
        logger.info("getting images")
        images = []
        msg = []
        has_images = user_message.get("images") is not None
        if has_images:
            logger.info("images found")
            body["messages"][-1]["images"] = None
            images = user_message.get("images")
        if not has_images:
            user_message_content = user_message.get("content")
            if user_message_content is not None and isinstance(
                user_message_content, list
            ):
                has_images = any(
                    item.get("type") == "image_url" for item in user_message_content
                )
                for item in user_message_content:
                    if item.get("type") == "image_url":
                        images.append(item)
                    else:
                        msg.append(item)
        logger.info(f"images: {images}")
        if has_images:
            ims = []
            try:
                for image in images:
                    img = Image.open(image)
                    a = np.asarray(img)
                    ims.append(str(a.tolist()))
                body["messages"][-1]["content"] = msg
                body["messages"][-1]["content"].append(ims)
            except Exception as e:
                return f"image list: {ims}"
            # if self.valves.vision_model_id:

            #     body["model"] = self.valves.vision_model_id
            #     if self.valves.status:
            #         await __event_emitter__(
            #             {
            #                 "type": "status",
            #                 "data": {
            #                     "description": f"Request routed to {self.valves.vision_model_id}",
            #                     "done": True,
            #                 },
            #             }
            #         )
            # else:
            #     if self.valves.status:
            #         await __event_emitter__(
            #             {
            #                 "type": "status",
            #                 "data": {
            #                     "description": "No vision model ID provided, routing could not be completed.",
            #                     "done": True,
            #                 },
            #             }
            #         )
        return body
