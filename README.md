# Clinical Note API Validation

Python pipeline for validating and map structured outputs extracted from unstructured clinical notes using biomedical APIs and ontologies.

The project validates three types of extracted clinical entities:

1. **Genes** using the **HGNC REST API**.
2. **HGVS variant descriptions** using the **Mutalyzer API**.
3. Patient-data **keywords** using the **OLS4 API** to retrieve matching **ontology terms**.

## What the Pipeline Does

For each clinical note, the pipeline:

1. Reads the structured JSON output.
2. Validates gene symbols against HGNC.
3. Validates HGVS descriptions with Mutalyzer.
4. Maps patient-data keywords to ontology terms using OLS4.
5. Creates a validated output JSON file.
6. Creates a separate error summary JSON file.

## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/clinical-note-ontology-validation.git
cd clinical-note-ontology-validation
```

Python 3.5 or later is needed. The script depends on standard libraries, plus the ones declared in [requirements.txt](requirements.txt).

Using a virtual environment is recommended:

```bash
python3 -m venv .env
source .env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Run the pipeline from the command line:

```bash
python main.py input.json validated_output.json validation_errors.json
```

Where:
- `input.json`: Input file with structured clinical-note data.
- `validated_output.json`: Output file containing the original data plus validation results and mapping to ontologies.
- `validation_errors.json`: Output file containing entities that could not be validated.

If you want to test the program, use [test/example_input.json](test/example_input.json) as input file.

#### Configuration

The configuration file [`config.py`](/config.py) contains API URLs and general settings used across the project.

The ontology mapper is configured with the `ONTOLOGY_VALIDATION_FIELDS` variable.

Each configuration item defines:

- `json_property`: the property name in the JSON input.
- `ontology`: the OLS ontology identifier used to validate values from that field.

Example:

```python
ONTOLOGY_VALIDATION_FIELDS = [
    {
        "json_property": "symptoms",
        "ontology": "hp"
    },
    {
        "json_property": "sex",
        "ontology": "ncit"
    }
]
```

This means:

- values in `symptoms` are validated against HPO (`hp`),
- values in `sex` are validated against NCIT (`ncit`).

To validate another JSON property, add a new dictionary to `ONTOLOGY_VALIDATION_FIELDS`.

Example:

```python
ONTOLOGY_VALIDATION_FIELDS = [
    {
        "json_property": "disease",
        "ontology": "ordo"
    }
]
```

## Input Format

The [input file](test/example_input.json) must be a JSON file containing a list of clinical-note records.

Each record must contain the following data elements:

    - `id`: Identifier of the subject or clinical note.
    - `unstructuredData`: Original unstructured clinical note.
    - `structuredData`: List containing the extracted structured fields.

Example from [test/example_input.json](test/example_input.json):

```json
[
    {
        "id": 1,
        "unstructuredData": "Test clinical note with genetic data as RFC1, and mutation NG_012232.1(NM_004006.2):c.93+1G>T; Symptoms are Diplopia and Oscillopsia",
        "structuredData": [
            {
                "geneticDiagnosis": [
                    "RFC1",
                    "testGene"
                ],
                "HGVS": [
                    "NG_012232.1(NM_004006.2):c.93+1G>T",
                    "test",
                    "NT_012232.1(NM_004006.2):c.93+1G>Z"
                ],
                "symptoms": [
                    "Diplopia",
                    "Oscillopsia",
                    "Oscillopsie",
                    "Test Data"
                ],
                "sex":["Male"]
            }
        ]
    }
]
```

### Supported fields

The pipeline validates three groups of structured data:

#### Gene fields

Gene symbols are validated against HGNC. Name of property must be `geneticDiagnosis`.

Example field:

```json
"geneticDiagnosis": [
    "RFC1"
]
```

#### HGVS fields

HGVS variant descriptions are validated with Mutalyzer. Name of property must be `HGVS`.

Example field:

```json
"HGVS": [
    "NG_012232.1(NM_004006.2):c.93+1G>T"
]
```

#### Ontology fields

Any field listed in ONTOLOGY_VALIDATION_FIELDS from the [`config.py`](/config.py) file is validated with OLS4.

Example field:

```json
"sex": [
    "Male"
]
```

## Output Files

The script creates two output files.

### 1. Validated Output JSON

This file contains the original clinical note data with an added `ontologyData` section.

Example:

```json
"ontologyData": {
    "geneticDiagnosis": [...],
    "HGVS": [...],
    "ontologyFields": {
        "symptoms": [...],
        "sex": [...],
        .
        .
        .
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

#### Example Ontology mapping Output

```json
{
    "keyword": "Male",
    "ontology": "ncit",
    "valid": true,
    "IRI": "http://purl.obolibrary.org/obo/NCIT_C20197",
    "ontologyId": "NCIT:C20197",
    "label": "Male",
    "ontologyName": "ncit",
    "matchType": "exact_search",
    "score": null,
    "synonyms": [
        "Human, Male",
        "M",
        "MALE",
        "Male",
        "male"
    ]
}
```

### 2. Validation Errors JSON

This file summarizes entities that could not be validated.

Example structure:

```json
{
    "unknownGenes": [],
    "invalidHGVS": [],
    "unknownOntologyTerms": []
}
```

Each item in unknownOntologyTerms includes the original JSON property so that failed mappings can be traced back to the configured input field.

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
- API results may change over time depending on updates in HGNC, Mutalyzer or/and OLS4.
- The semantic ontology fallback may return broad or imperfect matches.
- Manual review is recommended for uncertain or low-confidence mappings.
- The current pipeline assumes that the relevant extracted data are available inside the first item of `structuredData`.

## Author

**Sergi Aguiló Castillo**, Data Steward, Medical Biosciences Dpt., Radboudumc - [ORCID](https://orcid.org/0000-0003-0830-5733)
