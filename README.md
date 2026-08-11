# Clinical Note API Validation

Python pipeline for validating structured outputs extracted from unstructured clinical notes using biomedical APIs and ontologies.

The project validates three types of extracted clinical entities:

1. **Genes** using the **HGNC REST API**.
2. **HGVS variant descriptions** using the **Mutalyzer API**.
3. Patient-data **Keywords** using the **OLS4 API** to retrieve matching **ontology terms**.

## What the Pipeline Does

For each clinical note, the pipeline:

1. Reads the structured JSON output.
2. Validates gene symbols against HGNC.
3. Validates HGVS descriptions with Mutalyzer.
4. Maps patient-data keywords to ontology terms using OLS4.
5. Creates a validated output JSON file.
6. Creates a separate error summary JSON file.


#### Configuration file

The configuration file [`config.py`](/config.py)Contains API URLs and general settings used across the project.

Current configuration file:

```python
# API base URLs
HGNC_BASE_URL = "https://rest.genenames.org"
MUTALYZER_BASE_URL = "https://v3.mutalyzer.nl/api"
OLS4_BASE_URL = "https://www.ebi.ac.uk/ols4/api"

# Request settings
REQUEST_TIMEOUT_SECONDS = 20

# API-specific settings
HGNC_MAX_REQUESTS_PER_SECOND = 8
OLS_LLM_MIN_SCORE = 0.85
OLS_ONTOLOGY = "hp" # HPO ontology as default
```

The OLS_ONTOLOGY variable defines which ontology is used by the ontology validator. By default, it is set to "hp" to validate symptom keywords against the Human Phenotype Ontology.

## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/clinical-note-ontology-validation.git
cd clinical-note-ontology-validation
```

Install the required Python package (Python environment always recommended):

```bash
python -m pip install -r requirements.txt
```

## Usage

Run the pipeline from the command line, where:
- `input.json`: Is your input file
- `validated_output.json`: Is your output file
- `validation_errors.json`: File with errors encountered with the keywords validated

```bash
python main.py input.json validated_output.json validation_errors.json
```

If you want to test the program, use [test/example_input.json](test/example_input.json) as input file.

## Input Format

The [input file](test/example_input.json) must be a JSON file following this expected structure example:

```json
[
    {
        "Subject": 1,
        "unstructuredData": "Test clinical note with genetic data as RFC1, and mutation NG_012232.1(NM_004006.2):c.93+1G>T; Symptoms are Diplopia and Oscillopsia",
        "products": [
            {
                "geneticDiagnosis": [
                    "RFC1"
                ],
                "patientData": [
                    "Diplopia",
                    "Oscillopsia"
                ],
                "HGVS": ["NG_012232.1(NM_004006.2):c.93+1G>T"]
            }
        ]
    }
]
```

### Supported Fields

The pipeline currently checks these fields inside `products[0]`:

```json
{
    "geneticDiagnosis": ["RFC1"],
    "patientData": ["Diplopia", "Oscillopsia"],
    "HGVS": ["NG_012232.1(NM_004006.2):c.93+1G>T"]
}
```

## Output Files

The script creates two output files.

### 1. Validated Output JSON

This file contains the original clinical note data with an added `ontologyData` section.

Example structure:

```json
{
    "Subject": 130,
    "unstructuredData": "...",
    "products": [...],
    "ontologyData": {
        "geneticDiagnosis": [...],
        "HGVS": [...],
        "patientData": [...]
    }
}
```

#### Example Gene Validation Output

```json
{
    "gene": "RFC1",
    "valid": true,
    "HGNCId": "HGNC:9969",
    "approvedSymbol": "RFC1",
    "geneName": "replication factor C subunit 1",
    "status": "Approved",
    "matchType": "approved_symbol"
}
```

#### Example patientData Validation Output

```json
{
    "keyword": "Diplopia",
    "valid": true,
    "IRI": "http://purl.obolibrary.org/obo/HP_0000651",
    "ontologyId": "HP:0000651",
    "label": "Diplopia",
    "ontologyName": "hp",
    "matchType": "exact_label_or_synonym"
}
```

#### Example HGVS Validation Output

```json
{
    "input": "NM_000059.4:c.7790G>A",
    "structurallyValid": true,
    "apiValid": true,
    "normalizedDescription": "NM_000059.4:c.7790G>A",
    "errors": []
}
```

### 2. Validation Errors JSON

This file summarizes entities that could not be validated.

Example structure:

```json
{
    "unknownGenes": [],
    "invalidHGVS": [],
    "unknownPatientData": []
}
```

## Notes on Validation

### HGNC Gene Validation

The gene validator first checks whether the input is an approved HGNC symbol. If no result is found, it checks previous symbols and aliases. This improves validation for clinical notes that may contain older gene names or alternative symbols.

### HGVS Validation

The HGVS validator uses a basic regular expression before calling Mutalyzer. This avoids unnecessary API calls for clearly invalid strings. However, the regular expression is not a complete HGVS grammar validator.

### Patient Data Ontology Mapping

The ontology validator first performs an exact search against ontology labels and synonyms in OLS4 search endpoint. If no exact result is found, it can use the OLS4 LLM search endpoint as a fallback. Semantic matches should be reviewed carefully, especially in clinical or research settings.

## Limitations

- The pipeline validates extracted structured data but does not perform the original text extraction from clinical notes.
- The HGVS local check only validates the basic format.
- API results may change over time depending on updates in HGNC, Mutalyzer or/and OLS4
- The semantic ontology fallback may return broad or imperfect matches.
- Manual review is recommended for uncertain or low-confidence mappings.

## Author

**Sergi Aguiló Castillo**, Data Steward, Medical Biosciences Dpt., Radboudumc - [ORCID](https://orcid.org/0000-0003-0830-5733)
