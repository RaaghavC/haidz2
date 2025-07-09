# Vision-Based Scraper Implementation

## Overview

This document describes the implementation of a truly autonomous, vision-based web scraper that uses multimodal AI to extract data from ANY archive website without prior knowledge or hardcoding.

## Key Innovation: From Selectors to Vision

### Traditional Approach (Old)
```python
# Hard-coded selectors for each site
if "archnet.org" in url:
    title = page.query_selector(".title-class")
    image = page.query_selector("img.main-image")
    # Breaks when website changes
```

### Vision-Based Approach (New)
```python
# AI understands what it sees
screenshot = await page.screenshot()
extracted_data = await vision_extractor.extract_with_vision(
    page, 
    ArchiveRecord,
    "Extract metadata for the main image on this page"
)
# Works on ANY website
```

## Architecture Components

### 1. True Agentic Orchestrator
Located in: `src/agent/true_agentic_orchestrator.py`

Implements the OODA (Observe-Orient-Decide-Act) loop:

```python
async def _cognitive_loop(self, page: Page):
    while True:
        # OBSERVE - Take screenshot, get HTML
        observation = await self._observe(page)
        
        # ORIENT - AI understands context
        context = await self._orient(page, observation)
        
        # DECIDE - AI chooses next action
        decision = await self._decide(page, context)
        
        # ACT - Execute the decision
        should_continue = await self._act(page, decision)
```

### 2. Vision-Based Extractor
Located in: `src/modules/vision_extractor.py`

Uses GPT-4o to extract structured data from visual content:

```python
async def extract_with_vision(self, page, schema):
    # 1. Take screenshot
    screenshot = await page.screenshot()
    
    # 2. Get HTML context
    html = await page.content()
    
    # 3. Ask AI to extract data
    response = self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot}"}},
                {"type": "text", "text": f"HTML: {html[:10000]}"}
            ]
        }]
    )
```

### 3. Image Verifier
Located in: `src/modules/image_verifier.py`

Pre-validates pages before extraction:

```python
async def verify_page(self, page) -> bool:
    # AI looks at screenshot and determines if it's an image page
    # Returns True/False - no hardcoding
```

### 4. Stealth Browser Manager
Located in: `src/utils/stealth_browser_manager.py`

Advanced anti-detection measures:
- Playwright-stealth integration
- Human-like behavior simulation
- Proxy rotation support
- Random delays and movements

## AI Decision Types

The AI can make these decisions autonomously:

1. **EXTRACT** - Current page has target data
2. **CLICK** - Navigate by clicking an element
3. **SEARCH** - Use search functionality
4. **NAVIGATE** - Go to a specific URL
5. **FINISH** - Task complete

## Testing Philosophy

### Generic Test Framework
Located in: `test_vision_based_scraper.py`

Key principles:
- **No hardcoded URLs** in core tests
- **No expected selectors** or structures
- **Pure AI understanding** validation
- **Works on ANY archive** provided

### Running Tests

```bash
# Quick test on single site
./run_generic_test.sh --quick

# Full test suite on multiple archives
./run_generic_test.sh

# Custom archives
./run_generic_test.sh --urls "https://any-archive.com" --search "term"
```

## Usage Examples

### Command Line Interface

```bash
# Basic usage with search
python main_enhanced.py https://www.archnet.org/ --search "Antakya"

# Direct collection scraping
python main_enhanced.py https://www.archnet.org/collections

# Custom output and settings
python main_enhanced.py https://example.com \
    --output results.csv \
    --max-pages 10 \
    --no-headless
```

### Python API

```python
from src.agent.true_agentic_orchestrator import TrueAgenticOrchestrator
from src.agent.config import AgentConfig

# Configure
config = AgentConfig(
    output_file="results.csv",
    max_results=50,
    headless=True
)

# Create orchestrator
orchestrator = TrueAgenticOrchestrator(
    target_url="https://any-archive.org/",
    search_query="historical photos",
    config=config,
    api_key="your-openai-key"
)

# Run
result = await orchestrator.run()
print(f"Extracted {result['items_scraped']} items")
```

## Advantages Over Traditional Scraping

1. **Zero Maintenance**: No selectors to update when sites change
2. **Universal Compatibility**: Works on any archive without modification
3. **Human-Like Understanding**: Sees and understands pages like a human
4. **Self-Documenting**: AI explains its decisions
5. **Future-Proof**: Adapts to new layouts automatically

## Performance Considerations

- **API Costs**: Each page analysis uses GPT-4o tokens
- **Processing Time**: ~3-5 seconds per page for vision analysis
- **Rate Limiting**: Built-in delays to respect server limits
- **Caching**: Consider caching AI decisions for repeated runs

## Security & Ethics

- **Respects robots.txt**: Can be configured to check
- **Rate limiting**: Human-like delays between requests
- **Stealth mode**: Avoids detection while being respectful
- **No aggressive scraping**: Designed for research, not bulk harvesting

## Troubleshooting

### Common Issues

1. **"No API key"**: Set `OPENAI_API_KEY` environment variable
2. **"Rate limit"**: Add delays or use different API key
3. **"Can't find images"**: AI might need better search terms
4. **"Blocked by site"**: Enable proxy rotation

### Debug Mode

```bash
# Run with visible browser for debugging
python main_enhanced.py https://example.com --no-headless --verbose
```

## Future Enhancements

1. **Multi-Model Support**: Add Claude, Gemini, local models
2. **Batch Processing**: Process multiple pages in parallel
3. **Learning Mode**: Save AI decisions for faster re-runs
4. **API Mode**: REST API for scraping-as-a-service
5. **Fine-tuning**: Train smaller models on extraction patterns

## Conclusion

This vision-based approach represents a paradigm shift in web scraping:
- From brittle selectors to robust vision
- From site-specific code to universal AI
- From maintenance burden to self-adapting system

The scraper truly embodies the principle: "Show it what you want, and it will find it."