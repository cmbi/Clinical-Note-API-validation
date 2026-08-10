import re
from urllib.parse import quote

from api_client import api_get_json
from config import MUTALYZER_BASE_URL


hgvs_cache = {}

# This is not a full HGVS grammar validator.
# It only filters obvious bad inputs before calling Mutalyzer.
HGVS_BASIC_PATTERN = re.compile(
    r"""
    ^
    (?P<reference>
        [A-Z]{1,4}_[0-9]+(?:\.[0-9]+)?
        |LRG_[0-9]+(?:t[0-9]+)?
        |[A-Za-z0-9_.()\-]+
    )
    \s*
    (?:\([A-Za-z0-9_.\-]+\)\s*)?
    :
    (?P<coord_type>[cgmnopr])\.
    (?P<edit>.+)
    $
    """,
    re.VERBOSE,
)


def validate_hgvs_structure(description):
    """
    Check whether the HGVS description has a basic HGVS-like structure.

    Args:
        description: HGVS description to check.

    Returns:
        (True, None) if the description looks structurally acceptable.
        (False, error_message) otherwise.
    """

    if description == "":
        return False, "Empty HGVS description"

    if HGVS_BASIC_PATTERN.match(description) is None:
        return False, "Expected HGVS-like format: reference:coordinate_type.edit"

    return True, None


def validate_hgvs_with_mutalyzer(description):
    """
    Validate and normalize an HGVS description with Mutalyzer.

    Args:
        description: HGVS description extracted from the structured output.

    Returns:
        Dictionary with structure validation, API validation, normalized 
        description and errors.
    """

    # If gene already found, retrieve the info from the cache
    if description in hgvs_cache:
        return hgvs_cache[description]

    # Checks if the structure is valid before sending the gene to the mutalyzer
    structurally_valid, structure_error = validate_hgvs_structure(description)

    if not structurally_valid:
        result = {
            "input": description,
            "structurallyValid": False,
            "apiValid": False,
            "normalizedDescription": None,
            "errors": [structure_error]
        }
        hgvs_cache[description] = result
        return result

    # Send Description to Mutalyzer
    encoded_description = quote(description, safe="")
    url = f"{MUTALYZER_BASE_URL}/normalize/{encoded_description}"
    response = api_get_json(url)

    if response is None:
        result = {
            "input": description,
            "structurallyValid": True,
            "apiValid": False,
            "normalizedDescription": None,
            "errors": ["Mutalyzer API request failed"]
        }
        hgvs_cache[description] = result
        return result

    # If Mutalyzer responds:
    errors = extract_mutalyzer_messages(response, "errors")
    normalized_description = response.get("normalized_description") or response.get("description")

    result = {
        "input": description,
        "structurallyValid": True,
        "apiValid": len(errors) == 0,
        "normalizedDescription": normalized_description,
        "errors": errors
        }

    hgvs_cache[description] = result
    return result


def extract_mutalyzer_messages(response, key):
    """
    Extract errors or warnings from a Mutalyzer response.

    Args:
        response: Mutalyzer API response.
        key: Field to extract.
    
    Returns:
        List of message strings.  
    
    """
    messages = response.get(key, [])

    if messages is None:
        return []

    if not isinstance(messages, list):
        return [str(messages)]

    extracted_messages = []

    for message in messages:
        if isinstance(message, dict):
            extracted_messages.append(
                str(message.get("details"))
            )
        else:
            extracted_messages.append(str(message))

    return extracted_messages
