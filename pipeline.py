from hgnc_validator import validate_gene_code
from hgvs_validator import validate_hgvs_with_mutalyzer
from hpo_validator import retrieve_hpo_id

def validate_clinical_notes(json_data):
    """
    Validate all clinical notes in the input JSON.

    Args:
        json_data: a list of clinical-note dictionaries

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
        "unknownSymptoms": [],
    }

    # Validate each clinical note
    for clinical_note in json_data:
        validated_note = validate_single_clinical_note(clinical_note)
        validated_notes.append(validated_note)

        subject = clinical_note.get("Subject")

        for gene_result in validated_note["ontologyData"]["GeneticDiagnosis"]:
            if not gene_result.get("valid"):
                error_summary["unknownGenes"].append({
                    "Subject": subject,
                    **gene_result,
                })

        for hgvs_result in validated_note["ontologyData"]["HGVS"]:
            if not hgvs_result.get("apiValid"):
                error_summary["invalidHGVS"].append({
                    "Subject": subject,
                    **hgvs_result,
                })

        for symptom_result in validated_note["ontologyData"]["Symptoms"]:
            if not symptom_result.get("valid"):
                error_summary["unknownSymptoms"].append({
                    "Subject": subject,
                    **symptom_result,
                })

    return validated_notes, error_summary


def validate_single_clinical_note(clinical_note):
    """
    Get information from structured data in product property

    Args:
        clinical_note: A single clinical note from the input

    Returns:
        Dictionary with the Gene data and symptoms validated
    """
    # By default, there is always 1 element in the list
    # Therefore, always take the first one
    product = product[0]

    genes = clean_list(product.get("GeneticDiagnosis"))
    symptoms = clean_list(product.get("Symptoms"))
    hgvs_descriptions = clean_list(product.get("HGVS"))

    gene_results = []
    for gene in genes:
        gene_results.append(validate_gene_code(gene))

    hgvs_results = []
    for description in hgvs_descriptions:
        hgvs_results.append(validate_hgvs_with_mutalyzer(description))

    symptom_results = []
    for symptom in symptoms:
        symptom_results.append(retrieve_hpo_id(symptom))

    return {
        "Subject": clinical_note.get("Subject"),
        "unstructuredData": clinical_note.get("unstructuredData"),
        "token_count": clinical_note.get("token_count"),
        "products": clinical_note.get("products", []),
        "status": clinical_note.get("status"),
        "ontologyData": {
            "GeneticDiagnosis": gene_results,
            "HGVS": hgvs_results,
            "Symptoms": symptom_results,
        },
    }

def clean_list(value):
    """
    Convert structured filed into a clean list of strings.

    Args:
        value: Value extracted from an structured field

    Returns:
        output: List of cleaned string values or empty list (if values are not correct)
    """

    if value is None or value == "" or value.upper() == 'NA':
        return []

    output = []
    for item in value:
        item = str(item).strip()
        if item != "":
            output.append(item)
    return output