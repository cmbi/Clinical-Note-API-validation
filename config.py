# API base URLs
HGNC_BASE_URL = "https://rest.genenames.org"
MUTALYZER_BASE_URL = "https://v3.mutalyzer.nl/api"
OLS4_BASE_URL = "https://www.ebi.ac.uk/ols4/api"

# Request settings
REQUEST_TIMEOUT_SECONDS = 20

# API-specific settings
HGNC_MAX_REQUESTS_PER_SECOND = 8
OLS_LLM_MIN_SCORE = 0.85
OLS_LLM_SEARCH = True

# Default ontology for general keyword validation
ONTOLOGY_VALIDATION_FIELDS = [
    {
        "field": "symptoms",
        "ontology":"hp" 
    },
    {
        "field": "sex",
        "ontology":"ncit"
    },   
]