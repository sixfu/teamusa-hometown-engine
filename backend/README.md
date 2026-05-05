# Team USA API — Backend

## Quick Start

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Configure environment variables
```bash
cp .env.example .env
# Edit .env and fill in GCP_PROJECT_ID and GEMINI_API_KEY
```

### 3. Run locally
```bash
python main.py
```

Visit http://localhost:5000/health to verify the server is running.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/hometowns?mode=olympic` | All hometowns with athlete counts |
| `GET /api/hometowns/by-state?mode=olympic` | Hometowns aggregated by state |
| `GET /api/hometowns/search?city_name=...&mode=olympic` | Search hometowns |
| `GET /api/sports?mode=olympic` | All sports with athlete counts |
| `GET /api/hometown/<hometown_id>?mode=olympic` | Hometown detail + AI story |
| `GET /api/region/sport-concentration?city_name=...&mode=olympic` | Sport concentration vs national average |
| `GET /api/sports/heatmap?sport_name=...&mode=olympic` | Geographic heatmap for a sport |
| `GET /api/compare?city1=...&state1=...&city2=...&state2=...&mode=olympic` | Compare two regions |

Pass `mode=paralympic` to any endpoint to use the Paralympic dataset.

## Deploy to Cloud Run

```bash
gcloud run deploy team-usa-api --source . --platform managed --region us-central1
```
