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
  - Upload Excel files with news items
  - Get Gemini-powered insights (classification, similarity scores, commentary)
  - Color-coded similarity heatmap (green for high relevance, red for low)
  - Interactive selection with "Keep?" checkboxes
  - Export to Excel or HTML
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
- **Python** 3.11+ (for backend)
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
   - `MODEL_FLASH`: Gemini model (default: gemini-2.0-flash-001)
   - `PORT`: Backend port (default: 5001)
   - `COMPOSE_WEEKLY_SIM_WEIGHT`: Similarity weight for Compose Weekly (0.0-1.0)

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
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

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

### Daily News
- `GET /api/daily/news` - Fetch daily news articles
- `GET /api/daily/news/<date>` - Get news for specific date

### Weekly Digest
- `GET /api/weekly/digests` - List all weekly digests
- `GET /api/weekly/digest/<id>` - Get specific digest
- `POST /api/weekly/generate` - Generate new weekly digest

### Compose Weekly
- `POST /api/compose-weekly/upload` - Upload Excel file
- `POST /api/compose-weekly/analyze` - Analyze with Gemini AI
- `POST /api/compose-weekly/export` - Export curated list

### Search
- `POST /api/search` - Search historical articles
- `GET /api/search/history` - Get search history

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
- **Python 3.11** - Runtime
- **Flask 3.0** - Web framework
- **Flask-CORS** - Cross-origin resource sharing
- **Vertex AI SDK** - Gemini and embeddings
- **Google Cloud Firestore** - NoSQL database
- **Google Cloud BigQuery** - Data warehouse
- **Google Cloud Storage** - Media storage
- **Google Discovery Engine** - Search service

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Google Cloud Run** - Serverless container platform
- **Google Cloud Build** - CI/CD pipeline
- **Nginx** - Frontend static file serving

## 🎯 Key Features Explained

### Compose Weekly Workflow

1. **Upload**: User uploads Excel file with columns: Title, URL, Date, Abstract, CI Comment
2. **Analysis**: Backend sends data to Gemini for:
   - Classification (relevant/not relevant)
   - Similarity scoring (0-100, how similar to existing content)
   - AI commentary (insights about the article)
3. **Review**: UI displays results with:
   - Color-coded similarity badges (green = high, red = low)
   - Gemini insights as plain text
   - Checkboxes to select items to keep
4. **Export**: Export selected items to Excel or HTML

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
- `docker/docker-compose.yml` - Production container setup
- `docker/docker-compose.dev.yml` - Development overrides
- `docker/cloudbuild.yaml` - CI/CD pipeline configuration

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
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## 📚 Additional Resources

- [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) - Complete Docker deployment guide
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
