# Historical Architecture Scraper 🏛️

An autonomous web scraping agent designed to intelligently extract metadata from digital archives for the "Historical Architecture in Disaster Zones" project.

## 🌟 Features

- **Autonomous Operation**: Uses a cognitive loop (Analyze → Plan → Execute → Verify) to adapt to different website structures
- **Self-Correction**: Automatically adjusts strategy when data quality is low
- **Semantic Field Mapping**: Intelligently maps website fields to required schema
- **Multiple Navigation Methods**: Supports pagination, infinite scroll, and next/previous navigation
- **Robust Data Validation**: Ensures data quality and completeness
- **CSV Export**: Generates properly formatted CSV with unique IDs

## 🏗️ Architecture

The agent consists of several specialized modules:

1. **Analyzer**: Inspects webpage DOM to identify patterns and data structures
2. **Planner**: Generates scraping strategies based on analysis
3. **Executor**: Performs the actual data extraction using Playwright
4. **Verifier**: Validates data quality and completeness
5. **DataHandler**: Manages CSV output and unique ID generation
6. **Orchestrator**: Coordinates the cognitive loop

## 📋 Requirements

- Python 3.11+
- Playwright (for browser automation)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/RaaghavC/haidz2.git
cd haidz2/historical-architecture-scraper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

## 📖 Usage

### Enhanced Scraper (for real-world archives)

```bash
python main_enhanced.py https://www.archnet.org/ --output archnet_data.csv
```

### Original Scraper

```bash
python main.py https://example-archive.org --output data.csv
```

### Options

- `--output, -o`: Output CSV file path (default: scraped_data.csv)
- `--max-pages, -p`: Maximum number of pages to scrape (default: 100)
- `--headless/--no-headless`: Run browser in headless mode (default: headless)
- `--max-retries, -r`: Maximum retry attempts for self-correction (default: 3)
- `--min-quality, -q`: Minimum quality threshold 0.0-1.0 (default: 0.6)
- `--save-intermediate`: Save data after each page (default: enabled)
- `--verbose, -v`: Enable verbose output

### Examples

```bash
# Basic usage
python main_enhanced.py https://www.archnet.org/

# Scrape Machiel Kiel archive
python main_enhanced.py http://www.nit-istanbul.org/kielarchive/

# With custom output and page limit
python main_enhanced.py https://archive.org/items --output archive_data.csv --max-pages 50

# Visible browser with verbose output
python main_enhanced.py https://library.org/photos --no-headless --verbose
```

## 📊 Output Schema

The scraper extracts the following fields:

| Field | Description |
|-------|-------------|
| Unique ID | Auto-generated ID following specific rules |
| Typ | Type of image (Modern Photo, Historical Image, etc.) |
| Title | Title of the item |
| CE Start/End Date | Common Era dates |
| AH Start/End Date | Anno Hegirae dates |
| Date photograph taken | When the photo was taken |
| Artist | Creator of the work |
| Photographer | Person who took the photograph |
| Collection | Source archive/collection |
| Inventory # | Archive's inventory number |
| ... | (and more fields) |

### Unique ID Generation

IDs are generated following these patterns:
- For scraped images: `XX_CollectionInitial_InventoryNumber`
- With photographer: `PhotographerInitial_CollectionInitial_InventoryNumber`

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test module
pytest tests/unit/test_analyzer.py -v
```

### Test-Driven Development

All modules were developed using TDD. Each module has comprehensive unit tests in the `tests/unit/` directory.

## 🏛️ Project Structure

```
historical-architecture-scraper/
├── src/
│   ├── agent/          # Main orchestrator and config
│   ├── modules/        # Core modules (analyzer, planner, etc.)
│   ├── models/         # Data models and schemas
│   ├── strategies/     # Archive-specific patterns
│   ├── utils/          # Utility functions
│   └── cli.py          # Command-line interface
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── main.py             # Entry point
├── main_enhanced.py    # Enhanced scraper entry point
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Implement your changes
5. Run tests to ensure everything works
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📜 License

This project is part of the "Historical Architecture in Disaster Zones" research project.

## 🙏 Acknowledgments

- Built with Playwright for reliable web automation
- Uses Pydantic for robust data validation
- Developed using Test-Driven Development principles

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
