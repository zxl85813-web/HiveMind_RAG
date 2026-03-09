"""
Image Parser Plugin — Uses VLM to describe images.

所属模块: batch.plugins
依赖模块: langchain_openai, app.batch.ingestion.protocol
注册位置: REGISTRY.md > Batch Engine > Plugins
"""

import base64
import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.batch.ingestion.core import BaseParser, IngestionContext, ParserRegistry
from app.batch.ingestion.protocol import ImageContent, ResourceMetadata, ResourceType, StandardizedResource


@ParserRegistry.register
class ImageParser(BaseParser):
    def __init__(self):
        # Initialize VLM
        # Using gpt-4o-mini as efficient vision model default
        try:
            self.model = ChatOpenAI(model="gpt-4o-mini", max_tokens=1000, temperature=0)
        except Exception as e:
            logger.warning(f"Failed to initialize VLM: {e}. Image parsing will be limited.")
            self.model = None

    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        """Check if file extension is a supported image format."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        return ext in ["jpg", "jpeg", "png", "bmp", "webp", "gif"]

    async def parse(self, file_path: str, context: IngestionContext = None) -> StandardizedResource:
        filename = os.path.basename(file_path)
        logger.info(f"🖼️ Parsing Image: {filename}")

        description = ""

        if self.model:
            try:
                # Read image and encode
                ext = os.path.splitext(filename)[1].lower().replace(".", "")
                mime_type = f"image/{ext}"
                if ext == "jpg":
                    mime_type = "image/jpeg"

                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

                message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Describe this image in detail for a knowledge base. Extract any visible text entirely. If it's a diagram, describe the relationships.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"},
                        },
                    ]
                )
                response = await self.model.ainvoke([message])
                description = str(response.content)
                logger.debug(f"Image description generated: {description[:100]}...")

            except Exception as e:
                logger.error(f"❌ VLM processing failed for {filename}: {e}")
                description = f"[Error processing image: {e!s}]"
        else:
            description = "[VLM model not initialized - check OPENAI_API_KEY]"

        # Construct Resource
        meta = ResourceMetadata(filename=filename, file_path=file_path, resource_type=ResourceType.OTHER)

        resource = StandardizedResource(meta=meta)
        resource.images.append(
            ImageContent(
                image_path=file_path,
                caption=description,
                ocr_text="",  # VLM usually puts OCR in description for now
                confidence=1.0,
            )
        )

        # Add description to raw text so it gets indexed by standard text embedding
        resource.raw_text = f"Image Description for {filename}:\n{description}"

        return resource
