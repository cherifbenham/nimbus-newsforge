#!/usr/bin/env python3
"""Initialize Firestore production configuration with prompt_daily."""

import os

from firebase_helpers import db

# Force production mode
os.environ['ENV'] = 'production'
os.environ['PROJECT_ID'] = 'fsa-amadeus-471508'

# Default prompt_daily configuration
prompt_daily = """You are a senior analyst specialized in the travel, tourism, and hospitality sectors. Your task is to curate a daily newsletter highlighting the most impactful news for industry professionals.

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

**Output:** JSON with categorized news items including title, summary, source, and relevance."""

config_data = {
    'prompt_daily': prompt_daily
}

try:
    db.collection('config').document('prod').set(config_data, merge=True)
    print('✅ Firestore config/prod.prompt_daily initialized successfully')
    print(f'   Prompt length: {len(prompt_daily)} characters')
except Exception as e:
    print(f'❌ Error initializing Firestore: {e}')
    raise
