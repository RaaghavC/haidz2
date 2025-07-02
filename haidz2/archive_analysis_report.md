# Historical Architecture Archive Analysis Report

## 1. Archnet.org

### Overview
- **Type**: Open-access digital library focused on architecture in Muslim societies
- **Content**: Architectural sites, collections, and authorities
- **JavaScript**: Required for dynamic content loading

### Structure
- **Main Sections**: Sites, Authorities, Collections, Search
- **Collections Page**: 
  - 167 total collections displayed 20 per page
  - Alphabetically sorted with pagination
  - Each collection has: Name, Primary Image, Record ID
- **URL Pattern**: 
  - Collections: `https://www.archnet.org/collections`
  - Individual collection: `https://www.archnet.org/collections/[ID]`
  - Sites: `https://www.archnet.org/sites/[ID]`

### Metadata Fields
- Collection name
- Primary image
- Record ID
- Publication status
- Type categorization (Aga Khan Collection, Architect's Archives, etc.)

### Scraping Considerations
- Uses IIIF (International Image Interoperability Framework)
- JavaScript rendering required
- Pagination with 20 items per page
- Google Analytics tracking

### Navigation Pattern
- Page-based pagination: `?page=1`, `?page=2`, etc.
- Total 9 pages for collections

---

## 2. Manar al-Athar (Oxford)

### Overview
- **Type**: Archaeological photo archive from Oxford University
- **Content**: Images of archaeological sites primarily in Middle East/Mediterranean
- **JavaScript**: Partial - site functions without it but some features require it

### Structure
- **Organization**: Geographic hierarchy (countries/regions)
- **Featured Collections**: Organized by location (Algeria, Arabia, Egypt, Syria, etc.)
- **Search Interface**: 
  - Simple search with autocomplete (min 3 characters)
  - Geographic search option
  - Advanced search available

### Display Options
- Thumbnail grid view
- List view
- Map view
- Results per page: 24, 48, 72, 120, 240

### Metadata Fields
- Filename
- Location/site name
- Geographic information
- Resource type
- Modification date

### Scraping Considerations
- Login optional but may provide additional features
- CSV export functionality available
- Sortable by: Relevance, Popularity, Colour, Type, Modified
- User collections supported

### URL Patterns
- Collections: `pages/collections_featured.php`
- Search: `pages/search.php?search=[query]`

---

## 3. SALT Research

### Overview
- **Type**: Digital archive/discovery system
- **Content**: Appears to be a comprehensive research archive
- **JavaScript**: REQUIRED - Site does not function without JavaScript

### Structure
- Discovery/search interface based on Ex Libris Primo
- Uses institutional identifiers: `vid=90GARANTI_INST:90SALT_VU1`

### Scraping Considerations
- **Major Challenge**: Fully JavaScript-dependent
- Would require browser automation (Selenium/Puppeteer)
- Uses Angular or similar SPA framework
- API endpoints may be accessible with proper authentication

### Recommendation
This site would require sophisticated scraping with browser automation tools due to its heavy JavaScript dependency.

---

## 4. Machiel Kiel Photographic Archive (NIT Istanbul)

### Overview
- **Type**: Personal photographic archive
- **Content**: Ottoman and Balkan architectural heritage photos from 1960s onwards
- **Size**: Thousands of photographs

### Structure
- Simple photo gallery format
- Thumbnail grid display
- Individual image pages

### Display Format
- Thumbnail view: 184x184 pixels
- Full-size view: 900x700 pixels
- Click-through from thumbnail to full image

### Metadata Fields
- Location name
- Brief descriptive caption
- Image dimensions

### Access
- Main archive: `http://www.nit-istanbul.org/kielarchive/`
- Contact required for additional information:
  - Dr. Grigor Boykov (griboykov@yahoo.com)
  - Dr. Maximilian Hartmuth (nit@nit-istanbul.org)

### Scraping Considerations
- Simple HTML structure
- Direct image links available
- Limited metadata
- No apparent pagination information in sample

---

## 5. Akkasah Center for Photography (NYU Abu Dhabi)

### Overview
- **Type**: Photography archive focusing on Arab world
- **Content**: Historical and contemporary photographs, emphasis on UAE
- **Notable Collection**: Yasser Alwan Collection (3,000+ photos from Egypt, 1900-1950)

### Access Information
- Main website: akkasah.org (currently showing certificate error)
- Contact: akkasah@nyu.edu
- Phone: +971-2-628-5531

### Content Types
- Studio portraits
- Family photographs
- Postcards
- Vernacular photography

### Technical Details
- Managed digital storage with forward-migration
- Intellectual property rights retained by photographers
- Collections presented as separate named collections

### Scraping Considerations
- Website currently inaccessible due to SSL certificate issues
- Would need to contact institution directly
- May have access restrictions

---

## Summary and Recommendations

### Easiest to Scrape
1. **Manar al-Athar**: Well-structured, offers CSV export, clear URL patterns
2. **Machiel Kiel Archive**: Simple HTML structure, direct image links

### Moderate Difficulty
3. **Archnet**: Requires JavaScript but has clear structure and patterns

### Most Challenging
4. **SALT Research**: Fully JavaScript-dependent, would require browser automation
5. **Akkasah**: Currently inaccessible, may require institutional access

### General Scraping Strategy
1. For JavaScript-heavy sites: Use Puppeteer or Selenium
2. For simple HTML sites: BeautifulSoup or similar HTML parsers
3. Always check for API endpoints or export functionality first
4. Respect robots.txt and rate limits
5. Consider contacting institutions for bulk data access