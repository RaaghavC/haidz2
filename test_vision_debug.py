#!/usr/bin/env python3
"""
Debug version to see exactly what the AI is analyzing.
"""

import asyncio
import os
import sys
import base64

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.stealth_browser_manager import StealthBrowserManager
import openai


async def debug_vision():
    """Debug what the AI sees."""
    
    test_url = "https://www.archnet.org/sites/2055"
    
    # Initialize
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    client = openai.Client(api_key=api_key)
    browser = StealthBrowserManager(headless=False)
    
    print(f"DEBUG: Vision Analysis of {test_url}")
    print("=" * 60)
    
    await browser.start()
    
    try:
        async with browser.new_page() as page:
            # Navigate
            print("Loading page...")
            await page.goto(test_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # Get page info
            title = await page.title()
            url = page.url
            
            print(f"Page Title: {title}")
            print(f"Final URL: {url}")
            
            # Take screenshot
            screenshot_bytes = await page.screenshot()
            screenshot_path = "screenshots/debug_vision.png"
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_bytes)
            print(f"Screenshot saved to: {screenshot_path}")
            
            # Encode for AI
            base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
            
            # Ask AI to describe what it sees
            print("\nAsking AI to analyze the page...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe what you see on this webpage. Is this a detail page for a single image/photo with metadata, or is it a listing/collection page? What specific elements do you see?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            print("\nAI Analysis:")
            print(response.choices[0].message.content)
            
            # Also check for media parameter
            if "media_content_id" in url:
                print("\nNote: URL contains media_content_id parameter")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    await browser.stop()
    print("\nDebug complete!")


if __name__ == "__main__":
    asyncio.run(debug_vision())