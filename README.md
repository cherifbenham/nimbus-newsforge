# CI Newsletter Generator

**AI-Powered Competitive Intelligence Newsletter System**

An intelligent newsletter generation platform that leverages Google Cloud AI (Gemini, Vertex AI) to automatically fetch, analyze, and curate competitive intelligence news.

## 🌟 Features

### Core Capabilities
- **Daily News Fetching**: Automated daily collection of competitive intelligence articles from web sources
- **AI-Powered Analysis**: Gemini 2.0 Flash integration for intelligent content classification and summarization
- **Weekly Digest Compilation**: Smart aggregation of daily news into comprehensive weekly newsletters
- **Compose Weekly**: Advanced feature allowing manual curation with AI-powered similarity scoring and insights
- **Search & Discovery**: Full-text search across historical news articles using Google Discovery Engine
- **Multi-Source Integration**: Firestore for real-time data, BigQuery for analytics, and Cloud Storage for media

### UI Features
- **Daily Newsletter View**: Browse and manage daily news articles
- **Weekly Digest View**: Review and export weekly compilations
- **Compose Weekly Interface**:
  - Upload Excel files or email (.eml) files with news items
  - Email parser automatically extracts news with categorization
  - Get Gemini-powered insights (classification, similarity scores, commentary)
  - Edit classifications with dropdown menu (Industry/Regulation, Competitors, M&A, Travel Providers, etc.)
  - Color-coded similarity heatmap (green for high relevance, red for low)
  - Interactive selection with "Keep?" checkboxes
  - Export to Excel, HTML, or generate AI-powered Weekly Newsletter Template
  - **Weekly Template Export**: Generate professional HTML newsletter with:
    - Executive-ready formatting with corporate styling
    - "Highlights of the Week" summary section
    - News organized by category with subsections
    - CI comments highlighted with special formatting
    - Ready-to-send HTML output
- **Advanced Search**: Query historical articles with filters and relevance scoring
- **Setup/Configuration**: Manage application settings and preferences

## 🏗️ Architecture

```
ci_newsletter/
├── client/                    # React + TypeScript Frontend
│   ├── src/
│   │   ├── pages/            # Main application pages
│   │   │   ├── DailyNewsletter.tsx
│   │   │   ├── WeeklyDigest.tsx
│   │   │   ├── ComposeWeekly.tsx
│   │   │   ├── SearchResults.tsx
│   │   │   └── Setup.tsx
│   │   ├── components/       # Reusable UI components
│   │   ├── backend/          # API integration layer
│   │   ├── dto/              # TypeScript interfaces
│   │   └── routes/           # React Router configuration
│   ├── Dockerfile            # Production container
│   └── Dockerfile.dev        # Development container
│
├── server/                    # Python + Flask Backend
│   ├── app.py                # Main Flask application
│   ├── news_fetcher.py       # Daily news collection
│   ├── digest_generation.py  # Weekly digest compiler
│   ├── compose_weekly.py     # Compose Weekly feature
│   ├── weekly_template_generator.py  # AI-powered newsletter template generation
│   ├── email_parser.py       # Email (.eml) file parser for news extraction
│   ├── news_search.py        # Discovery Engine integration
│   ├── firebase_helpers.py   # Firestore operations
│   ├── bigquery_helpers.py   # BigQuery operations
│   ├── utils.py              # Shared utilities
│   ├── config/               # Firestore prompts & configs
│   └── requirements.txt      # Python dependencies
│
├── cloud_run_job/            # GCP Cloud Run job for automated fetching
│   ├── main.py               # Job entry point
│   └── Dockerfile            # Job container
│
├── scripts/                   # Utility scripts
│   ├── start_dev.sh          # Start development servers
│   ├── stop_dev.sh           # Stop development servers
│   └── sync_bq_to_firestore.py
│
├── docker/docker-compose.yml         # Production Docker setup
├── docker/docker-compose.dev.yml     # Development Docker override
├── docker/cloudbuild.yaml           # CI/CD configuration
├── docker/deploy-to-gcp.sh          # GCP deployment script
└── .env                      # Environment configuration
```

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.12+ (for backend)
- **Google Cloud Project** with the following APIs enabled:
  - Vertex AI API
  - Firestore API
  - BigQuery API
  - Cloud Storage API
  - Discovery Engine API
- **Service Account** with appropriate permissions
- **Docker** (optional, for containerized deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ci_newsletter
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your GCP project details
   ```

   Key environment variables:
   - `PROJECT_ID`: Your GCP project ID
   - `REGION`: GCP region (default: europe-west4)
   - `MODEL_FLASH`: Gemini model (default: gemini-2.0-flash-exp)
   - `PORT`: Backend port (default: 5001)
   - `COMPOSE_WEEKLY_SIM_WEIGHT`: Similarity weight for Compose Weekly (0.0-1.0)
   - `CORS_ORIGINS`: Comma or semicolon-separated allowed origins (supports regex patterns like `https://*.run.app`)
   - `FIRESTORE_DATABASE_ID`: Firestore database identifier (default: (default))
   - `COMPOSE_WEEKLY_PROMPT_LOCAL_ONLY`: Set to 'true' to prevent prompt syncing to Firestore

3. **Place your service account credentials**
   ```bash
   # Place your service account JSON file in the root directory
   # It should match the pattern configured in .env
   ```

4. **Start development servers**
   ```bash
   # Automated startup (recommended)
   ./scripts/start_dev.sh

   # Or manually:
   # Backend
   cd server
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python app.py

   # Frontend (in new terminal)
   cd client
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5001/api

### Docker Development

```bash
# Start with hot-reload enabled
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

# Access at:
# - Frontend: http://localhost:5173
# - Backend: http://localhost:5001
```

## 🌐 Deployment to Google Cloud Platform

### Option 1: Automated Deployment Script

```bash
chmod +x docker/deploy-to-gcp.sh
./docker/deploy-to-gcp.sh
```

This will:
- Build Docker images for backend and frontend
- Push to Google Container Registry
- Deploy to Cloud Run
- Configure environment variables
- Return service URLs

### Option 2: Google Cloud Build (CI/CD)

The repository includes `docker/cloudbuild.yaml` for automated CI/CD:

```bash
# Trigger build manually
gcloud builds submit --config=docker/cloudbuild.yaml

# Or connect to GitHub for automatic deployments
gcloud builds triggers create github \
  --repo-name=<your-repo-name> \
  --repo-owner=<your-github-username> \
  --branch-pattern="^main$" \
  --build-config=docker/cloudbuild.yaml
```

### Option 3: Manual Docker Deployment

See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for detailed instructions.

## 📋 API Endpoints

### Health & Status
- `GET /api/health` – Basic health check
- `GET /api/health/deps` – Validates Firestore, BigQuery and Vertex AI connectivity

### Newsletters
- `GET /api/newsletters` – List latest newsletters
- `POST /api/newsletters` – Create or save a newsletter record
- `PUT /api/newsletters/<newsletter_id>` – Update an existing newsletter
- `DELETE /api/newsletters/<newsletter_id>` – Remove a newsletter
- `POST /api/newsletters/generate` – Ask Gemini to generate newsletter content
- `POST /api/newsletters/email/compose` – Generate compact email content from curated news
- `POST /api/newsletters/email/compose/curated` – Generate curated email with highlights

### Digests
- `GET /api/digests` – List weekly digests
- `POST /api/digests` – Create or save a digest record
- `PUT /api/digests/<digest_id>` – Update digest metadata
- `DELETE /api/digests/<digest_id>` – Remove a digest
- `POST /api/digests/generate` – Build digest content for a date range
- `POST /api/digests/highlight/generate` – Regenerate digest highlights
- `POST /api/digests/metadata` – Upload supporting metadata

### News Data
- `GET /api/news` – Query Firestore news items by date, site, or ranking
- `POST /api/news/analyze` – Run Gemini analysis on one article
- `GET /api/news/url/<url_hash>` – Fetch news by hashed URL
- `GET /api/news/search?input=...` – Search historical items via Discovery Engine

### Compose Weekly
- `POST /api/compose-weekly/parse-emails` – Parse uploaded .eml files into news items
- `POST /api/compose-weekly/analyze` – Generate Gemini insights for selected rows
- `GET /api/compose-weekly/prompt` – Retrieve the Compose Weekly prompt
- `PUT /api/compose-weekly/prompt` – Update the prompt (unless disabled via env)
- `POST /api/compose-weekly/generate-template` – Produce the HTML weekly newsletter

## 🔧 Technology Stack

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **React Router** - Client-side routing
- **Axios** - HTTP client

### Backend
- **Python 3.12** - Runtime (ensures prebuilt wheels for gRPC and other dependencies)
- **Flask 3.0** - Web framework
- **Flask-CORS** - Cross-origin resource sharing with regex pattern support
- **Vertex AI SDK** - Gemini 2.0 Flash for content generation and embeddings
- **Google Cloud Firestore** - NoSQL database
- **Google Cloud BigQuery** - Data warehouse
- **Google Cloud Storage** - Media storage
- **Google Discovery Engine** - Search service
- **BeautifulSoup4** - HTML parsing for email content extraction
- **Python email library** - MIME email parsing for .eml files

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Google Cloud Run** - Serverless container platform
- **Google Cloud Build** - CI/CD pipeline
- **Nginx** - Frontend static file serving

## 🎯 Key Features Explained

### Compose Weekly Workflow

1. **Upload**: User uploads either:
   - **Excel file** with columns: Title, URL, Date, Abstract, CI Comment
   - **Email files (.eml)**: Parser automatically extracts news items with section categorization
2. **Analysis**: Backend sends data to Gemini for:
   - Classification into categories (Industry/Regulation, Competitors, M&A, Travel Providers, Research & Reports, etc.)
   - Similarity scoring (0-100, how similar to existing content)
   - AI commentary (insights about the article)
3. **Review & Edit**: UI displays results with:
   - **Editable classifications**: Dropdown menu to adjust Gemini's categorization
   - Color-coded similarity badges (green = high, red = low)
   - Gemini insights as plain text
   - Checkboxes to select items to keep
   - Add/edit CI comments for strategic context
4. **Export**: Multiple export options:
   - **Excel**: Tabular data export for offline review
   - **HTML**: Simple HTML table format
   - **Weekly Newsletter Template** (NEW): AI-generated professional newsletter with:
     - Executive greeting and summary
     - "Highlights of the Week" section
     - News organized by category with proper formatting
     - CI comments highlighted with special styling
     - Corporate-ready HTML suitable for email distribution

### Weekly Template Generation

The **Export Weekly Template** feature uses Gemini AI to transform selected news items into a polished HTML newsletter:

- **Smart Categorization**: News automatically grouped by classification (Airlines, Competitors, M&A, etc.)
- **Executive Summary**: AI generates compelling "Highlights of the Week" with 3-5 key stories
- **Professional Styling**: Exact HTML formatting with:
  - Arial font, consistent spacing
  - Color scheme: #000835 (text), #3A8BFF (headers/borders), #c5d5f9 (CI comments background)
  - Proper HTML entities for professional rendering
- **CI Commentary**: Strategic insights displayed in italicized, highlighted paragraphs
- **Subsections**: Travel Providers automatically split into Airlines, Airports, Hospitality, Financials
- **One-Click Export**: Generates and downloads complete HTML file ready for distribution

### Email Parser (.eml Support)

Upload email files directly to extract news items:
- **Section Detection**: Automatically identifies news sections (Top News, North America, Europe, Asia Pacific, etc.)
- **Field Extraction**: Parses title, date, abstract, URL, and category from email structure
- **Batch Processing**: Upload multiple .eml files simultaneously
- **HTML Parsing**: Handles complex email HTML formats with BeautifulSoup
- **Smart Categorization**: Maps email sections to `class_daily` field for classification

### Similarity Scoring

The system uses Vertex AI text embeddings (text-embedding-005) to calculate similarity between new articles and historical content. The similarity weight (`COMPOSE_WEEKLY_SIM_WEIGHT`) controls the influence of embedding similarity vs. metadata matching.

### AI-Powered Insights

Gemini 2.0 Flash analyzes each article for:
- **Relevance**: Is this competitive intelligence?
- **Novelty**: How unique is this compared to existing content?
- **Key Points**: What are the main takeaways?

## 📊 Data Flow

```
News Sources → Cloud Run Job (Daily) → Firestore
                                      ↓
                                   BigQuery
                                      ↓
User uploads Excel → Backend API → Gemini Analysis
                                      ↓
                                 Similarity Check
                                      ↓
                              Results to Frontend
```

## 🔐 Security

- All sensitive credentials stored in `.env` (git-ignored)
- Service account JSON files excluded via `.gitignore`
- CORS configured for localhost and production domains
- Environment-specific configurations
- No hardcoded secrets in codebase

## 🛠️ Development Scripts

```bash
# Start development environment
./scripts/start_dev.sh

# Stop development environment
./scripts/stop_dev.sh

# Sync BigQuery to Firestore
python scripts/sync_bq_to_firestore.py

# Convert Excel to Compose Weekly format
python scripts/excelfy_compose_weekly.py
```

## 📝 Configuration Files

- `.env` - Environment variables and API keys
- `server/config/dev.prompt_weekly_compose` - Gemini prompt for Compose Weekly
- `server/config/compose_weekly_prompt.txt` - Template generation prompt
- `docker/docker-compose.yml` - Production container setup
- `docker/docker-compose.dev.yml` - Development overrides
- `docker/cloudbuild.yaml` - CI/CD pipeline configuration

## 🆕 Recent Enhancements (October 2025)

### Email Parser Integration
- **Multi-file Upload**: Support for uploading multiple .eml files simultaneously
- **Section Intelligence**: Automatically detects and categorizes news by email sections
- **Robust Parsing**: Handles various email formats with HTML content extraction
- **Data Mapping**: Maps email structure to ComposeWeeklyItem schema with validation

### Editable Classifications
- **Dropdown Interface**: Change Gemini classifications directly in the UI
- **Predefined Categories**: Industry/Regulation, Competitors, M&A & Investments, Travel Providers, Research & Reports, Tech Updates
- **Real-time Updates**: Changes immediately reflected in the table
- **Export Consistency**: Selected classifications preserved in all export formats

### Weekly Newsletter Template Export
- **AI-Powered Generation**: Gemini creates executive-ready HTML newsletters
- **Template Compliance**: Follows exact styling from reference templates
- **Smart Highlights**: AI selects and summarizes 3-5 most important stories
- **Category Organization**: Automatic grouping with subsections (Airlines, Airports, etc.)
- **CI Commentary Integration**: Strategic insights highlighted with professional formatting
- **One-Click Export**: Downloads complete HTML file with date-stamped filename

### CORS Enhancement
- **Regex Pattern Support**: Allows wildcard domains like `*.run.app`
- **Multi-Environment**: Supports localhost and Cloud Run deployments
- **Flexible Configuration**: Environment variable driven CORS origins

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 5001 is in use
lsof -ti :5001 | xargs kill -9

# Restart
.venv/bin/python server/app.py
```

### Frontend build errors
```bash
# Clear cache and reinstall
cd client
rm -rf node_modules dist
npm install
```

### Gemini API errors
- Verify `MODEL_FLASH` is set correctly in `.env`
- Check service account has Vertex AI permissions
- Ensure billing is enabled on GCP project

### Docker issues
```bash
# Clean up and rebuild
docker compose down -v
docker compose build --no-cache
docker compose up
```

## 📎 Appendix: Extended Documentation

This appendix consolidates the in-depth docs that previously lived under `docs/README.md`. Use it when you need full specs, historical deployment notes, or product ideation context beyond the main setup instructions.

### Weekly Template Export Feature

#### Overview
This feature allows users to generate a formatted HTML newsletter from selected news items using Gemini AI. The newsletter follows a specific template structure with professional styling suitable for executive audiences.

#### Implementation

##### Backend Components

**`server/weekly_template_generator.py`** – Generates the template via Gemini.

```python
def generate_weekly_template(news_items: List[Dict[str, str]], week_info: str = None) -> str
```

Key capabilities:
- Uses Gemini 2.0 Flash for generation
- Produces an opening greeting and "Highlights of the week"
- Organizes items across categories (Industry / Regulation, Competitors, M&A & Investments, Travel Providers, Research & Reports, Trend of the Week, Tech Updates)
- Applies exact corporate HTML styling
- Displays CI comments with highlighted formatting

**`POST /api/compose-weekly/generate-template`** (defined in `server/app.py`).

Request body:
```json
{
  "news_items": [
    {
      "title": "string",
      "abstract": "string",
      "url": "string",
      "gemini_classification": "string",
      "ci_comment": "string",
      "gemini_comment": "string"
    }
  ],
  "week_info": "string (optional)"
}
```
Response:
```json
{
  "status": "ok",
  "html": "string"
}
```

##### Frontend Components
- `client/src/backend/ApiHelper.tsx` exposes `generateWeeklyTemplate(...)`.
- `client/src/pages/ComposeWeekly.tsx` adds `isGeneratingTemplate`, `hasCheckedItems`, and `handleExportWeeklyTemplate()` to call the API and download the HTML file. Button styling reflects loading/disabled states.

#### Template Structure
1. **Opening greeting** introducing the week
2. **Highlights of the Week** with 3-5 top stories
3. **Categorized sections**:
   - Industry / Regulation → General Industry News
   - Competitors → Sabre, Travelport, Google, Accelya
   - M&A and Investments (no subsections)
   - Travel Providers → Airlines, Intermediaries, Hospitality, Airports
   - Financials (no subsections)
   - Research and Reports (no subsections)
4. **News item formatting**: bold title + summary, extracted source link, optional CI comment highlighted in blue, section dividers, H2 subsections.

#### Section Hierarchy & Mapping
- Gemini receives explicit instructions for each section/subsection.
- Classifications map to subsections (e.g., "Travel Providers - Airlines" → Travel Providers / Airlines).
- Empty sections/subsections must not render.

| Classification Input | Section | Subsection |
| --- | --- | --- |
| Industry / Regulation | Industry / Regulation | General Industry News |
| Competitors - Sabre | Competitors | Sabre |
| Competitors - Travelport | Competitors | Travelport |
| Competitors - Google | Competitors | Google |
| Competitors - Accelya | Competitors | Accelya |
| M&A and Investments | M&A and Investments | (none) |
| Travel Providers - Airlines | Travel Providers | Airlines |
| Travel Providers - Intermediaries | Travel Providers | Intermediaries |
| Travel Providers - Hospitality | Travel Providers | Hospitality |
| Travel Providers - Airports | Travel Providers | Airports |
| Financials | Financials | (none) |
| Research and Reports | Research and Reports | (none) |

Fallback behavior: if Gemini receives an unknown classification it chooses the closest section but still hides empty areas.

#### Workflow & Testing
1. Upload Excel/email items
2. Run analysis, edit classifications, mark `keep`
3. Add CI comments
4. Click **Export Weekly Template** → API call → download HTML

Testing tips:
- Use `data/test_weekly_template_input.json` for regression coverage.
- Generate HTML locally:
  ```bash
  curl -X POST http://localhost:5001/api/compose-weekly/generate-template \
    -H "Content-Type: application/json" \
    -d @data/test_weekly_template_input.json \
    -s | jq -r '.html' > /tmp/test_output.html
  open /tmp/test_output.html
  ```
- Keep the fixture updated when adding new subsections.

#### Operational Notes
- Temperature 0.7, max 8000 tokens, ensures creativity with control.
- HTML cleanup strips fenced code blocks if Gemini emits them.
- Future ideas: UI week-info override, HTML preview, template catalog, emailing workflow.

### Deployment Report (October 2025)

> Archival record of the initial Cloud Run go-live. For current automation see `docker/deploy-to-gcp.sh` and `instructions.md`.

#### Executive Summary & Architecture
- React + Vite frontend (served by Nginx) and Flask backend (Python 3.12) deployed to Cloud Run.
- Integrations: Firestore, BigQuery, Vertex AI (Gemini), Discovery Engine, Cloud Storage.
- Serverless architecture with auto-scaling, IAM-secured service account, Cloud Build for CI.

#### Timeline Highlights
1. **Cloud Build substitutions** – Added `client/cloudbuild.yaml` to pass `_VITE_API_URL` / `_IMAGE_NAME` during builds.
2. **Backend deployment** – `gcloud run deploy ci-newsletter-backend ... --set-env-vars ...` with 1Gi RAM, 1 CPU, 0-10 instances, `CORS_ORIGINS` defaults.
3. **Frontend deployment** – Multi-stage Docker build, `gcloud run deploy ci-newsletter-frontend ...` pointing to backend URL.
4. **CORS fixes** – Switched to semicolon-separated env vars and regex-friendly parsing; ultimately locked CORS to the exact frontend URL for simplicity and security.
5. **gcloud CLI setup** – Recorded troubleshooting for missing CLI install, PATH fixes, and authentication steps.
6. **Build details** – Documented Dockerfile, dependencies, image digests, and Cloud Run revision metadata.

#### Final Architecture Diagram
```
Users -> Cloud Run Frontend (Nginx, port 8080) -> Cloud Run Backend (Flask, port 5001)
                                               -> Service Account -> Firestore / BigQuery / Vertex AI
```

### README Update Summary (October 2025)

Key improvements made during the large README refresh:
1. Expanded UI features, Compose Weekly workflow, and Weekly Template export documentation.
2. Updated architecture diagrams and component lists (added `weekly_template_generator.py`, `email_parser.py`).
3. Added new API endpoints (Compose Weekly parse/generate/prompt routes).
4. Enhanced environment configuration guidance (model defaults, CORS regex patterns, Firestore DB flag, prompt-sync toggle).
5. Documented recent enhancements (email parser integration, editable classifications, template export, CORS regex support).

Future documentation ideas: screenshots, .eml samples, generated HTML example, walkthrough video, API request/response snippets.

### Product Notes Scratchpad

Loose product/UX notes captured during stakeholder sessions:
- Weekly newsletter should include AI ranking, clustering, and short contextual CI comments.
- Daily digests use regional clustering; weekly moves to sector/industry grouping.
- Upload "daily digest" artifacts in their original format for automated parsing.
- Compose Weekly classifications must remain editable with prompt guidance per class.
- Validation items: HTML compatibility of weekly output, customizable ranking criteria, limit total curation time to ~2h/week.


## 📚 Additional Resources

- [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) - Complete Docker deployment guide
- Appendix above (Weekly Template, deployment log, product notes) for deep dives
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Vertex AI Gemini API](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)

## 📄 License

All rights reserved

## 👥 Contributors

Cherif Benham
---

**Last Updated**: October 2025
