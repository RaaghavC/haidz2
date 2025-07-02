# AI-Agentic Historical Architecture Scraper

A truly autonomous, AI-powered web scraper that intelligently extracts architectural metadata from any digital archive.

## 🚀 Features

- **ONE unified entry point** - Just run `scrape.py`
- **AI Brain** - Intelligently analyzes archives and selects optimal extraction strategy
- **Search Filtering** - Extract only what you need with search queries
- **Multiple Strategies** - API, specialized scrapers, and browser automation
- **CSV Output** - Properly formatted with all metadata fields
- **True Autonomy** - Works on ANY archive, not just hardcoded ones

## 📦 Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## 🎯 Usage

```bash
python3 scrape.py [ARCHIVE_URL] [SEARCH_QUERY]
```

### Examples

**ArchNet - Search for specific mosque:**
```bash
python3 scrape.py https://www.archnet.org "habib-i neccar mosque"
```

**Wikimedia - Search for city architecture:**
```bash
python3 scrape.py https://commons.wikimedia.org "antakya"
```

**Manar al-Athar - Search for Damascus:**
```bash
python3 scrape.py https://www.manar-al-athar.ox.ac.uk "damascus"
```

## 🧠 How It Works

1. **AI Analysis** - The AI brain analyzes the target URL
2. **Strategy Selection** - Chooses the best extraction method:
   - Known archives use specialized strategies (ArchNet → Algolia API)
   - Unknown archives use API detection or browser automation
3. **Data Extraction** - Executes with search filtering
4. **CSV Output** - Saves results with proper unique IDs (XX_ prefix)

## 📊 Output Format

Results are saved to `scraped_data.csv` with all metadata fields:
- Unique ID (XX_ prefix for scraped images)
- Title, Type, Dates
- Photographer, Copyright
- Location, Collection
- Image URLs (content and IIIF)
- And more...

## 🏗️ Architecture

```
scrape.py (Entry Point)
    ↓
AI Brain (ai_brain.py)
    ↓
Strategy Selection
    ├── ArchNetStrategy (Algolia API)
    ├── WikimediaStrategy (MediaWiki API)  
    ├── ManarStrategy (Browser)
    ├── APIDetectionStrategy (Auto-detect)
    └── BrowserAutonomousStrategy (Fallback)
    ↓
Data Handler (CSV Output)
```

## 🔧 Options

- `--output FILE` - Output CSV file (default: scraped_data.csv)
- `--max-results N` - Maximum results to extract (default: 500)
- `--verbose` - Enable verbose logging

## 🎯 Supported Archives

**Specialized Support:**
- ArchNet (archnet.org)
- Wikimedia Commons
- Manar al-Athar
- SALT Research
- Machiel Kiel Archive

**Works on ANY archive** through autonomous browser extraction!

## 📝 Notes

- The system uses the XX_ prefix for all scraped images (photographer unknown)
- Search queries filter across all text fields
- API detection attempts to find hidden endpoints
- Browser strategy analyzes DOM patterns autonomously