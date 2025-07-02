# Historical Architecture Scraper - Development Documentation

## Project Overview

This is an autonomous web scraping agent designed to intelligently extract metadata from digital archives for the "Historical Architecture in Disaster Zones" project. The agent operates on a cognitive loop principle: Analyze → Plan → Execute → Verify, with self-correction capabilities.

## Architecture

### Core Principles

1. **Cognitive Loop**: The agent follows a dynamic analysis approach, not static scripts
2. **Dynamic Analysis**: Real-time inspection of website structure without pre-written parsers
3. **Semantic Deduction**: Maps unstructured web data to structured schema intelligently
4. **Self-Correction**: Recognizes flaws and automatically adjusts strategy

### Components

- **Agent Orchestrator**: Main controller managing the cognitive loop
- **Analyzer**: DOM inspection and pattern recognition
- **Planner**: Strategy generation from analysis results
- **Executor**: Playwright-based scraping execution
- **Verifier**: Data validation and quality checks
- **DataHandler**: CSV output and Unique ID generation

## Development Progress

### Completed
- [x] Architectural design and planning
- [x] Project structure setup
- [x] Git repository initialization
- [x] DataHandler module implementation (TDD) - CSV output, unique ID generation
- [x] Data models (schemas.py, strategies.py) - Pydantic models for data structures
- [x] Analyzer module implementation (TDD) - DOM inspection and pattern recognition
- [x] Planner module implementation (TDD) - Strategy generation from analysis
- [x] Executor module implementation (TDD) - Playwright integration and scraping
- [x] Verifier module implementation (TDD) - Data validation and quality checks
- [x] Agent orchestrator implementation - Cognitive loop management
- [x] CLI interface - Command-line interface with Click
- [x] Main entry point - main.py
- [x] Comprehensive README.md - User documentation

### In Progress
- [ ] Integration tests for complete workflow
- [ ] GitHub repository setup and push

### Future Enhancements
- [ ] Advanced semantic mapping with NLP
- [ ] Machine learning for pattern recognition
- [ ] Support for more archive types
- [ ] API interface
- [ ] Web UI for monitoring

## Testing Strategy

All modules are developed using Test-Driven Development (TDD):
1. Write failing tests first
2. Implement minimal code to pass tests
3. Refactor for clarity and efficiency
4. Commit when tests pass

## Data Schema

The agent extracts the following fields in order:
- Unique ID (generated)
- Typ
- Title
- CE Start Date
- CE End Date
- AH Start Date
- AH End Date
- Date photograph taken
- Date Qualif.
- Medium
- Technique
- Measurements
- Artist
- Orig. Location
- Collection
- Inventory #
- Folder
- Photographer
- Copyright for Photo
- Image Quality
- Image Rights
- Published in
- Notes

## Unique ID Generation Rules

Primary Format (if Photographer known): `PhotographerInitial_Museum/LocationInitial_Image#`
Fallback Format (if Photographer unknown): `TypeInitial_LocationInitial_Image#`

### Mappings

**Photographer Initials**:
- PDB: Patricia Blessing
- RPM: Richard P. McClary
- FH: Fatih Han
- BTO: Belgin Turan Özkaya
- MME: Menna M. ElMahy
- MLK: Michelle Lynch Köycü
- NN: No Name/Unknown

**Type Initials**:
- MP: Modern Photo
- HI: Historical Image
- PC: Postcard
- SS: Screenshot
- SC: Scan
- PT: Painting
- IT: Illustration

## Key Technical Decisions

1. **Async/Await**: All web interactions are asynchronous for efficiency
2. **Playwright**: Chosen for JavaScript-heavy sites and reliability
3. **Pydantic**: Data validation and schema enforcement
4. **Pytest**: Comprehensive testing framework
5. **Type Hints**: Full typing for better IDE support and error catching

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run tests
pytest

# Run the scraper
python main.py --url "https://example-archive.org"
```

## Development Workflow

1. Check todo list with TodoRead
2. Select task and mark as in_progress
3. Write tests first (TDD)
4. Implement functionality
5. Run tests and fix failures
6. Refactor if needed
7. Commit with detailed message
8. Mark task as completed
9. Push to GitHub

## Error Handling

- Network failures: Retry with exponential backoff
- Parsing errors: Log and attempt alternative strategies
- Missing data: Mark fields as None, continue processing
- Critical failures: Save partial data, provide detailed error report