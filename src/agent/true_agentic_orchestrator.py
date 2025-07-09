"""
True Agentic Orchestrator with Observe-Orient-Decide-Act Loop
This implements the vision-based autonomous scraping agent as outlined in the plan.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import base64
from enum import Enum

from playwright.async_api import Page
import openai
from pydantic import BaseModel

from src.agent.config import AgentConfig
from src.agent.autonomous_navigator import AutonomousNavigator
from src.models.schemas import ArchiveRecord, DataSchema
from src.modules.vision_extractor import VisionBasedExtractor
from src.modules.image_verifier import ImageVerifier
from src.modules.data_handler import DataHandler
from src.utils.stealth_browser_manager import StealthBrowserManager

# Set up logging
logger = logging.getLogger(__name__)


class AgentAction(str, Enum):
    """Possible actions the agent can take"""
    EXTRACT = "EXTRACT"
    CLICK = "CLICK"
    SEARCH = "SEARCH"
    NAVIGATE = "NAVIGATE"
    FINISH = "FINISH"


class AgentDecision(BaseModel):
    """Decision made by the agent"""
    action: AgentAction
    reason: str
    target: Optional[str] = None  # CSS selector or URL for action
    confidence: float = 0.0


class TrueAgenticOrchestrator:
    """
    A truly autonomous scraping agent that uses vision and AI to make decisions.
    Follows the Observe-Orient-Decide-Act (OODA) loop pattern.
    """
    
    def __init__(
        self,
        target_url: str,
        search_query: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the true agentic orchestrator.
        
        Args:
            target_url: Starting URL for scraping
            search_query: Optional search term
            config: Agent configuration
            api_key: OpenAI API key
        """
        self.target_url = target_url
        self.search_query = search_query
        self.config = config or AgentConfig()
        
        # Initialize OpenAI client
        self.client = openai.Client(api_key=api_key)
        
        # Initialize components
        self.browser_manager = StealthBrowserManager(
            headless=self.config.headless,
            use_stealth=True
        )
        self.vision_extractor = VisionBasedExtractor(self.client)
        self.image_verifier = ImageVerifier(self.client)
        self.navigator = AutonomousNavigator(
            api_key=api_key,
            provider="openai"
        )
        self.data_handler = DataHandler()
        
        # State management
        self.extracted_data = []
        self.visited_urls = set()
        self.current_page_url = None
        self.actions_taken = []
        
        logger.info(f"Initialized True Agentic Orchestrator")
        logger.info(f"Target: {target_url}")
        logger.info(f"Search: {search_query}")
        
    async def run(self) -> Dict[str, Any]:
        """
        Run the agentic scraping process.
        
        Returns:
            Dictionary with results and metadata
        """
        start_time = datetime.now()
        
        try:
            # Start browser
            await self.browser_manager.start()
            
            async with self.browser_manager.new_page() as page:
                # Navigate to starting URL
                await page.goto(self.target_url, wait_until="networkidle")
                self.current_page_url = page.url
                
                # If we have a search query, try to use it first
                if self.search_query:
                    search_performed = await self._try_search(page, self.search_query)
                    if search_performed:
                        logger.info("Search performed successfully")
                        await page.wait_for_timeout(3000)
                
                # Main OODA loop
                loop_count = 0
                max_loops = self.config.max_pages * 10  # Safety limit
                
                while loop_count < max_loops:
                    loop_count += 1
                    
                    # OBSERVE - Get current state
                    observation = await self._observe(page)
                    
                    # ORIENT - Understand context
                    context = await self._orient(page, observation)
                    
                    # DECIDE - Choose action
                    decision = await self._decide(page, context)
                    
                    # Log decision
                    logger.info(f"Loop {loop_count}: Action={decision.action}, Reason={decision.reason}")
                    self.actions_taken.append({
                        "loop": loop_count,
                        "action": decision.action,
                        "reason": decision.reason,
                        "url": page.url
                    })
                    
                    # ACT - Execute decision
                    should_continue = await self._act(page, decision)
                    
                    if not should_continue:
                        logger.info("Agent decided to finish")
                        break
                    
                    # Check if we have enough data
                    if len(self.extracted_data) >= self.config.max_results:
                        logger.info(f"Reached max results: {self.config.max_results}")
                        break
                
            # Save results
            if self.extracted_data:
                self._save_results()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "items_scraped": len(self.extracted_data),
                "duration": duration,
                "actions_taken": self.actions_taken,
                "data": self.extracted_data
            }
            
        except Exception as e:
            logger.error(f"Critical error in orchestrator: {str(e)}")
            if self.extracted_data:
                self._save_results()
            
            return {
                "success": False,
                "error": str(e),
                "items_scraped": len(self.extracted_data),
                "data": self.extracted_data
            }
            
        finally:
            await self.browser_manager.stop()
    
    async def _observe(self, page: Page) -> Dict[str, Any]:
        """
        OBSERVE phase: Gather information about current state.
        
        Args:
            page: Current page
            
        Returns:
            Observation data
        """
        # Take screenshot
        screenshot_bytes = await page.screenshot()
        base64_screenshot = base64.b64encode(screenshot_bytes).decode("utf-8")
        
        # Get page HTML (truncated)
        html_content = await page.content()
        
        # Get current URL
        current_url = page.url
        
        # Get page title
        title = await page.title()
        
        # Count links
        links = await page.query_selector_all("a")
        
        return {
            "screenshot": base64_screenshot,
            "html_snippet": html_content[:5000],  # First 5k chars
            "url": current_url,
            "title": title,
            "link_count": len(links),
            "visited_before": current_url in self.visited_urls
        }
    
    async def _orient(self, page: Page, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        ORIENT phase: Analyze and understand the current context.
        
        Args:
            page: Current page
            observation: Data from observe phase
            
        Returns:
            Context analysis
        """
        # Use AI to understand the page type and content
        prompt = f"""Analyze this webpage and determine its type and content.

Current URL: {observation['url']}
Page Title: {observation['title']}
Number of links: {observation['link_count']}
Previously visited: {observation['visited_before']}

Based on the screenshot and HTML, answer:
1. What type of page is this? (homepage, search results, collection listing, image detail, etc.)
2. Does this page contain individual image/photo records?
3. Are there navigation elements to get to image records?
4. What is the main content of this page?

Provide your response as a JSON object with these fields:
- page_type: The type of page
- has_target_content: Boolean, true if page has individual image records
- navigation_available: Boolean, true if there are ways to navigate deeper
- content_summary: Brief description of main content
- relevant_elements: List of relevant elements seen (search boxes, image links, etc.)
"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing web pages for digital archives and museums."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{observation['screenshot']}"
                            }
                        },
                        {"type": "text", "text": f"HTML snippet:\n{observation['html_snippet']}"}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        context = json.loads(response.choices[0].message.content)
        context["observation"] = observation
        
        return context
    
    async def _decide(self, page: Page, context: Dict[str, Any]) -> AgentDecision:
        """
        DECIDE phase: Choose the next action based on context.
        
        Args:
            page: Current page
            context: Context from orient phase
            
        Returns:
            Agent decision
        """
        # Build decision prompt
        prompt = f"""Based on the current page analysis, decide the next action.

Context:
- Page type: {context.get('page_type', 'unknown')}
- Has target content: {context.get('has_target_content', False)}
- Navigation available: {context.get('navigation_available', False)}
- Items already extracted: {len(self.extracted_data)}
- Goal: Find and extract metadata from individual image/photo records

Available actions:
1. EXTRACT - Extract data from current page (only if it shows a single image record)
2. CLICK - Click on a specific element to navigate
3. SEARCH - Use search functionality (if available and not used yet)
4. NAVIGATE - Go to a different URL
5. FINISH - Complete the scraping task

Previous actions taken: {len(self.actions_taken)}

Choose the most appropriate action and provide your response as a JSON object with:
- action: One of [EXTRACT, CLICK, SEARCH, NAVIGATE, FINISH]
- reason: Brief explanation of why this action
- target: For CLICK provide simple CSS selector (e.g., "a.link-class") or text content (e.g., "View Images"). For SEARCH provide search term. For NAVIGATE provide URL.
- confidence: Confidence level (0.0-1.0)
"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an autonomous web scraping agent. Make strategic decisions to efficiently find and extract image metadata."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{context['observation']['screenshot']}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        decision_data = json.loads(response.choices[0].message.content)
        
        return AgentDecision(**decision_data)
    
    async def _act(self, page: Page, decision: AgentDecision) -> bool:
        """
        ACT phase: Execute the decided action.
        
        Args:
            page: Current page
            decision: Decision to execute
            
        Returns:
            True to continue, False to stop
        """
        try:
            if decision.action == AgentAction.EXTRACT:
                # Verify this is actually an image page
                is_image_page = await self.image_verifier.verify_page(page)
                
                if is_image_page:
                    logger.info(f"Extracting data from: {page.url}")
                    extracted = await self.vision_extractor.extract_with_vision(
                        page,
                        ArchiveRecord
                    )
                    
                    # Add URL to extracted data
                    extracted["source_url"] = page.url
                    self.extracted_data.append(extracted)
                    
                    logger.info(f"Successfully extracted record #{len(self.extracted_data)}")
                else:
                    logger.warning("Page verification failed - not an image page")
                
                # Mark URL as visited
                self.visited_urls.add(page.url)
                
                # Go back to continue browsing
                await page.go_back()
                await page.wait_for_timeout(2000)
                
            elif decision.action == AgentAction.CLICK:
                if decision.target:
                    logger.info(f"Clicking element: {decision.target}")
                    try:
                        # Try different selector approaches
                        element = None
                        
                        # First try as direct CSS selector
                        try:
                            element = await page.query_selector(decision.target)
                        except:
                            pass
                        
                        # If that fails, try text-based selectors
                        if not element and "text=" in decision.target:
                            text = decision.target.split("text=")[1].strip('"\'')
                            locator = page.get_by_text(text).first
                            element = await locator.element_handle()
                        elif not element and ":contains(" in decision.target:
                            # Handle jQuery-style contains selector
                            text = decision.target.split(":contains(")[1].rstrip(")")
                            text = text.strip("'\"")
                            locator = page.get_by_text(text, exact=False).first
                            element = await locator.element_handle()
                        elif not element:
                            # Try to find by partial text match
                            locator = page.get_by_text(decision.target, exact=False).first
                            element = await locator.element_handle()
                        
                        if element:
                            await element.click()
                            await page.wait_for_timeout(3000)
                        else:
                            logger.warning(f"Could not find element: {decision.target}")
                    except Exception as e:
                        logger.error(f"Error clicking: {str(e)}")
                
            elif decision.action == AgentAction.SEARCH:
                if decision.target and self.search_query:
                    logger.info(f"Performing search for: {self.search_query}")
                    await self._try_search(page, self.search_query)
                    await page.wait_for_timeout(3000)
                
            elif decision.action == AgentAction.NAVIGATE:
                if decision.target:
                    logger.info(f"Navigating to: {decision.target}")
                    await page.goto(decision.target, wait_until="networkidle")
                
            elif decision.action == AgentAction.FINISH:
                logger.info("Agent decided to finish task")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing action {decision.action}: {str(e)}")
            # Continue despite errors
            return True
    
    async def _try_search(self, page: Page, search_term: str) -> bool:
        """
        Try to find and use search functionality.
        
        Args:
            page: Current page
            search_term: Term to search
            
        Returns:
            True if search was performed
        """
        search_selectors = [
            'input[type="search"]',
            'input[name="q"]',
            'input[name="query"]',
            'input[name="search"]',
            'input[placeholder*="search" i]',
            'input[class*="search" i]'
        ]
        
        for selector in search_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    await self.browser_manager.fill_input(page, selector, search_term)
                    await page.keyboard.press("Enter")
                    return True
            except:
                continue
        
        return False
    
    def _save_results(self):
        """Save extracted data to CSV."""
        if not self.extracted_data:
            return
        
        # Convert to ArchiveRecord objects
        records = []
        for data in self.extracted_data:
            try:
                record = ArchiveRecord(**data)
                records.append(record)
            except Exception as e:
                logger.error(f"Error creating record: {str(e)}")
        
        if records:
            self.data_handler.save_to_csv(records, self.config.output_file)
            logger.info(f"Saved {len(records)} records to {self.config.output_file}")