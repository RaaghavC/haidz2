
"""
Vision-Based Extractor using Multimodal LLMs
"""

import base64
import json
from typing import Dict, Any, Type
from playwright.async_api import Page
import openai
from pydantic import BaseModel

class VisionBasedExtractor:
    """
    Extracts structured data from a webpage using vision (screenshot) and HTML.
    This approach is resilient to changes in website layout.
    """

    def __init__(self, client: openai.Client):
        """
        Initialize the extractor with an OpenAI client.
        """
        self.client = client

    async def extract_with_vision(
        self,
        page: Page,
        schema: Type[BaseModel],
        prompt_text: str = "Based on the screenshot and HTML, extract the required data for the main subject of the page. Focus on the primary information presented."
    ) -> Dict[str, Any]:
        """
        Extracts data from a page using a multimodal LLM.

        Args:
            page: The Playwright page to extract from.
            schema: The Pydantic schema for the data to be extracted.
            prompt_text: The instruction to the LLM.

        Returns:
            A dictionary containing the extracted data.
        """
        # 1. Take a screenshot
        screenshot_bytes = await page.screenshot()
        base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")

        # 2. Get HTML content
        html_content = await page.content()

        # 3. Construct the prompt
        json_schema = schema.model_json_schema()

        response = self.client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o for better vision performance and cost
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert data extractor for historical architecture archives. Extract ALL visible information from the webpage screenshot and HTML, formatting it into JSON that conforms to the provided schema. Look for metadata in tables, info boxes, and descriptions. Extract dates, locations, dimensions, collections, and all other visible fields. Use null for truly missing fields, but extract everything you can see."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{prompt_text}\n\nIMPORTANT: Look at ALL visible text on the page including tables, metadata sections, file information, and descriptions. Extract data for ALL fields in this JSON schema, using null only for truly missing values:\n{json.dumps(json_schema, indent=2)}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"  # High detail for better extraction
              