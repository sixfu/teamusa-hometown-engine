import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    BQ_DATASET_ID = 'team_usa_olympics'

    # BigQuery table names — Olympic
    BQ_ATHLETES_TABLE = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.athletes'
    BQ_HOMETOWNS_TABLE = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.hometowns'
    BQ_SPORTS_TABLE = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.sports'

    # BigQuery table names — Paralympic
    BQ_ATHLETES_TABLE_PARA = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.athletes_para'
    BQ_HOMETOWNS_TABLE_PARA = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.hometowns_para'
    BQ_SPORTS_TABLE_PARA = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.sports_para'

    # Shared aggregated tables
    BQ_SPORT_YEAR_COUNTS_TABLE = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.athletes_counts_by_sport_year'
    BQ_SPORT_YEAR_COUNTS_TABLE_PARA = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.para_athletes_counts_by_sport_year'

    # Sport prediction table
    BQ_ATHLETES_4PREDICTSPORT_TABLE = f'{GCP_PROJECT_ID}.{BQ_DATASET_ID}.athletes_4predictsport'

    # Gemini model config
    GEMINI_MODEL = 'gemini-2.5-flash-lite'
    GEMINI_REGION = 'us-central1'

    DEBUG = os.getenv('DEBUG', 'True') == 'True'
