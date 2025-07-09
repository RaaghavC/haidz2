"""
Image Verifier using Multimodal LLMs
"""

import base64
from typing import Dict, Any
from playwright.async_api import Page
import openai

class ImageVerifier:
    """
    Verifies if a webpage is primarily about an image.
    """

    def __init__(self, client: openai.Client):
        """
        Initialize the verifier with an OpenAI client.
        """
        self.client = client

    async def verify_page(
        self,
        page: Page
    ) -> bool:
        """
        Verifies if the page is primarily about an image.

        Args:
            page: The Playwright page to verify.

        Returns:
            True if the page is primarily about an image, False otherwise.
        """
        # 1. Take a screenshot
        screenshot_bytes = await page.screenshot()
        base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")

        # 2. Construct the prompt
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing digital archive websites. Determine if this webpage shows a SINGLE image/photo detail page (with metadata), not a listing or collection page. Respond ONLY with 'YES' or 'NO'."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Is this a detail page for a SINGLE historical image/photo with its metadata (not a listing page)? Answer YES or NO only."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "low"  # Low detail is sufficient for page type detection
                            }
                        }
                    ]
                }
   