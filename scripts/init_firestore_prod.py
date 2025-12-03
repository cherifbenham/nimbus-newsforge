#!/usr/bin/env python3
"""Initialize Firestore production configuration."""

import os
import sys

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

# Set environment variables
os.environ['ENV'] = 'production'
os.environ['PROJECT_ID'] = 'nimbus-newsforge'

from firebase_helpers import db

# Default prompt_daily configuration
prompt_daily = '''You are a senior analyst specialized in the travel, tourism, and hospitality sectors. Your task is to curate a daily newsletter highlighting the most impactful news for industry professionals.

**Focus Areas:**
- Airlines, GDS, travel technology
- Hotels, accommodations, vacation rentals
- Online travel agencies (OTAs), metasearch
- Ground transportation, car rentals
- Travel management, corporate travel
- Tourism boards, destinations
- Travel retail, payments

**Selection Criteria:**
- Business impact: Funding, M&A, partnerships, product launches
- Market trends: Shifts in consumer behavior, regulatory changes
- Competitive intelligence: Strategic moves by key players
- Innovation: New technologies, digital transformation

**Output:** JSON with categorized news items including title, summary, source, and relevance.'''

config_data = {
    'prompt_daily': prompt_daily
}

print('Initializing Firestore config/prod...')
db.collection('config').document('prod').set(config_data, merge=True)
print('✅ Firestore config/prod.prompt_daily initialized successfully')
print('\nYou can now use the Daily Newsletter feature at:')
print('https://ci-newsletter-frontend-816103265049.us-central1.run.app')
