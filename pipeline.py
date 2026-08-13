from hgnc_validator import validate_gene_code
from hgvs_validator import validate_hgvs_with_mutalyzer
from ontology_validator import validate_ontology_term
from config import ONTOLOGY_VALIDATION_FIELDS

def validate_clinical_notes(json_data):
    """
    Validate all clinical notes in the input JSON.

    Args:
        json_data: A list of clinical-note dictionaries.

    Returns:
        validated_notes, error_summary
    """
    ## Initialise variables
    # If file is a dictionary, convert it to a list
    if isinstance(json_data, dict):
        json_data = [json_data]

    validated_notes = []
    error_summary = {
        "unknownGenes": [],
        "invalidHGVS": [],
        "unknownOntologyTerms": [],
    }

    # Validate each clinical note
    for clinical_note in json_data:
        validated_note = validate_single_clinical_note(clinical_note)
        validated_notes.append(validated_note)

        subject = clinical_note.get("id")

        for gene_result in validated_note["ontologyData"]["geneticDiagnosis"]:
            if not gene_result.get("valid"):
                error_summary["unknownGenes"].append({
                    "id": subject,
                    **gene_result,
                })

        for hgvs_result in validated_note["ontologyData"]["HGVS"]:
            if not hgvs_result.get("valid"):
                error_summary["invalidHGVS"].append({
                    "id": subject,
                    **hgvs_result,
                })

        configured_fields = validated_note["ontologyData"]["ontologyFields"]
        for field_name, field_results in configured_fields.items():
            for ontology_result in field_results:
                if not ontology_result.get("valid"):
                    error_summary["unknownOntologyTerms"].append({
                        "id": subject,
                        "jsonProperty": field_name,
                        **ontology_result,
                    })

    return validated_notes, error_summary


def validate_single_clinical_note(clinical_note):
    """
    Get information from structured data in structured fields

    Args:
        clinical_note: A single clinical note from the input

    Returns:
        Dictionary with the Gene data and patient data validated
    """
    # By default, there is always 1 element in the list
    # Therefore, always take the first one
    structured_data_values = clinical_note.get("structuredData")[0]

    genes = clean_list(structured_data_values.get("geneticDiagnosis"))
    hgvs_descriptions = clean_list(structured_data_values.get("HGVS"))

    gene_results = []
    for gene in genes:
        gene_results.append(validate_gene_code(gene))

    hgvs_results = []
    for description in hgvs_descriptions:
        hgvs_results.append(validate_hgvs_with_mutalyzer(description))

    ontology_results = validate_ontology_fields(structured_data_values)


    return {
        "id": clinical_note.get("id"),
        "unstructuredData": clinical_note.get("unstructuredData"),
        "structuredData": clinical_note.get("structuredData", []),
        "ontologyData": {
            "geneticDiagnosis": gene_results,
            "HGVS": hgvs_results,
            "ontologyFields": ontology_results,
        },
    }

def validate_ontology_fields(structured_data_values):
    """
    Validate JSON properties configured in ONTOLOGY_VALIDATION_FIELDS.

    Args:
        structured_data_values: Structured fields in the dictionary

    Returns:
        Dictionary with validation results grouped by JSON property name.
    """

    ontology_results = {}

    for field_config in ONTOLOGY_VALIDATION_FIELDS:
        field_property = field_config["field"]
        ontology = field_config["ontology"]

        # For each value in the clinical note realted to the property
        values_property = structured_data_values.get(field_property)
        values_property = clean_list(values_property)

        ontology_results[field_property] = []

        for keyword in values_property:
            ontology_results[field_property].append(
                validate_ontology_term(
                    keyword=keyword,
                    ontology=ontology
                )
            )

    return ontology_results

def clean_list(value):
    """
    Convert structured filed into a clean list of strings.

    Args:
        value: Value extracted from an structured field

    Returns:
        output: List of cleaned string values or empty list (if values are not correct)
    """

    if value is None or value == "" or str(value).upper() == 'NA':
        return []

    output = []
    for item in value:
        item = str(item).strip()
        if item != "":
            output.append(item)
    return output