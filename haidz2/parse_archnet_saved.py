#!/usr/bin/env python3
"""
Parse saved ArchNet HTML to extract sites data.
"""

import json
import re
from bs4 import BeautifulSoup

# Read the saved HTML
with open('archnet_debug.html', 'r') as f:
    content = f.read()

# Parse with BeautifulSoup
soup = BeautifulSoup(content, 'html.parser')

# Find __NEXT_DATA__
script_tag = soup.find('script', id='__NEXT_DATA__')
if script_tag:
    try:
        data = json.loads(script_tag.string)
        sites = data.get('props', {}).get('pageProps', {}).get('sites', [])
        
        print(f"Found {len(sites)} sites in the page")
        
        if sites:
            # Extract and format first 5 sites
            for i, site in enumerate(sites[:5]):
                # Extract image URL
                image_url = ''
                primary_image = site.get('primary_image', {})
                if primary_image and primary_image.get('child'):
                    child = primary_image['child']
                    image_url = child.get('content_thumbnail_url', '')
                
                # Extract location
                place = site.get('place', {})
                location = place.get('place_name', '') if place else ''
                
                # Extract type
                site_types = site.get('site_types', [])
                site_type = site_types[0].get('name', '') if site_types else ''
                
                print(f"\n{i+1}. Site ID: {site.get('id')}")
                print(f"   Title: {site.get('name', 'No title')}")
                print(f"   Location: {location}")
                print(f"   Type: {site_type}")
                print(f"   Has Image: {'Yes' if image_url else 'No'}")
                
            # Save formatted data
            formatted_sites = []
            for site in sites:
                # Extract all fields
                primary_image = site.get('primary_image', {})
                image_url = ''
                if primary_image and primary_image.get('child'):
                    child = primary_image['child']
                    image_url = child.get('content_thumbnail_url', '')
                
                place = site.get('place', {})
                location = place.get('place_name', '') if place else ''
                
                site_types = site.get('site_types', [])
                site_type = site_types[0].get('name', '') if site_types else ''
                
                formatted_sites.append({
                    'id': site.get('id'),
                    'title': site.get('name', ''),
                    'location': location,
                    'type': site_type,
                    'image_url': image_url,
                    'collection': 'ArchNet',
                    'inventory_num': str(site.get('id', '')),
                    'description': site.get('notes', '')
                })
            
            # Save to JSON for easy import
            with open('archnet_sites.json', 'w') as f:
                json.dump(formatted_sites, f, indent=2)
            
            print(f"\n✅ Saved {len(formatted_sites)} formatted sites to archnet_sites.json")
            
    except Exception as e:
        print(f"Error parsing data: {e}")
else:
    print("No __NEXT_DATA__ found in the HTML")