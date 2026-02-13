#!/usr/bin/env python3
"""
Query Immich API for all assets and print their updatedAt dates.
"""

import requests
import os
from dotenv import load_dotenv

# Load .env file from EXIF directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

IMMICH_URL = os.environ.get('IMMICH_URL') or 'http://localhost:2283'
IMMICH_API_KEY = os.environ.get('IMMICH_API_KEY') or 'your_api_key_here'

headers = {
    'x-api-key': IMMICH_API_KEY,
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

try:
    resp = requests.get(f'{IMMICH_URL}/api/assets', headers=headers)
    resp.raise_for_status()
    assets = resp.json()
    print(f'Total assets: {len(assets)}')
    print('Sample updatedAt:')
    for asset in assets[:10]:
        print(f"ID: {asset.get('id')}, updatedAt: {asset.get('updatedAt')}")

    dates = [asset.get('updatedAt') for asset in assets if asset.get('updatedAt')]
    if dates:
        print(f'Earliest updatedAt: {min(dates)}')
        print(f'Latest updatedAt: {max(dates)}')
    else:
        print('No updatedAt dates found.')
except Exception as e:
    print(f"Error querying Immich API: {e}")
    exit(1)
