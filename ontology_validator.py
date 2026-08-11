from api_client import api_get_json
from config import OLS4_BASE_URL, OLS_LLM_MIN_SCORE, OLS_ONTOLOGY


ontology_cache = {}


def validate_ontology_term(keyword, use_llm_fallback=True):
    """
    Retrieve an ontology mapping for a keyword.

    Strategy:
        1. Exact OLS search on a given ontology label and synonyms.
        2. If not found, optional OLS LLM semantic search.

    Args:
        keyword: String with the keyword.
        use_llm_fallback: Use OLS LLM search if no argument is given.

    Returns:
        Dictionary with the mapping result.
    """

    if keyword in ontology_cache:
        return ontology_cache[keyword]

    if keyword == "":
        result = empty_ontology_result(keyword, match_type="exact_search", error="Empty ontology result")
        ontology_cache[keyword] = result
        return result

    # Try exact search function in OLS
    exact_result = exact_ontology_search(keyword)

    if exact_result["valid"] or not use_llm_fallback:
        ontology_cache[keyword] = exact_result
        cache_synonyms(exact_result)
        return exact_result

    # If no results in the exact search, use LLM search
    # It always takes a while to do the LLM searches
    llm_result = llm_ontology_search(keyword)

    if llm_result["valid"]:
        ontology_cache[keyword] = llm_result
        cache_synonyms(llm_result)
        return llm_result

    ontology_cache[keyword] = exact_result
    return exact_result


def exact_ontology_search(keyword):

    """
    Search for an exact ontology match using OLS labels and synonyms.

    Args:
        keyword: Ontology label to search.

    Returns:
        Dictionary with the ontology validation result.

    """
    url = f"{OLS4_BASE_URL}/search"
    params = {
        "q": keyword,
        "ontology": OLS_ONTOLOGY,
        "exact": "true",
        "obsoletes": "false",
        "fieldList": "iri,label,ontology_name,synonym,short_form,obo_id",
        "queryFields": "label,synonym",
    }

    response = api_get_json(url, params=params)

    if response is None:
        return empty_ontology_result(keyword, match_type="exact_search", error="OLS API request failed")

    docs = response.get("response", {}).get("docs", [])

    if len(docs) == 0:
        return empty_ontology_result(keyword, match_type="not_found")

    return ontology_result_from_ols_doc(keyword, docs[0], match_type="exact_label_or_synonym")


def llm_ontology_search(keyword):
    """
    Search for a semantic ontology match using the OLS LLM search endpoint.

    Args:
        keyword: Ontology label to search.

    Returns:
        Dictionary with the ontology validation result.

    """


    url = f"{OLS4_BASE_URL}/v2/ontologies/{OLS_ONTOLOGY}/classes/llm_search"
    params = {
        "q": keyword,
        "page": 0,
        "size": 1,
        "lang": "en",
        "model": "llama-embed-nemotron-8b_pca512",
        "isDefiningOntology": "false",
        "includeCurations": "true",
    }

    response = api_get_json(url, params=params)

    if response is None:
        return empty_ontology_result(keyword, match_type="llm_search", error="OLS LLM search request failed")

    elements = response.get("elements", [])

    if len(elements) == 0:
        return empty_ontology_result(keyword, match_type="llm_search", error="OLS LLM have found no results")

    hit = elements[0]
    score = hit.get("score")

    if score < OLS_LLM_MIN_SCORE:
        result = empty_ontology_result(keyword, match_type="llm_search", error="llm_below_threshold")
        result["score"] = score
        return result

    return ontology_result_from_ols_doc(
        keyword,
        hit,
        match_type="llm_semantic",
        score=score,
    )

def ontology_result_from_ols_doc(input_keyword, doc, match_type, score=None):

    """
    Convert one OLS result into a standard ontology result.

    Args:
        input_keyword: Original ontology label from the structured output.
        doc: OLS document returned by the API.
        match_type: Type of match used to find the ontology term.
        score: Optional semantic search score.

    Returns:
        Dictionary with standardized ontology information.
    """
    
    synonyms = doc.get("synonym", [])
    if synonyms is None:
        synonyms = []
    elif not isinstance(synonyms, list):
        synonyms = [str(synonyms)]

    return {
        "keyword": input_keyword,
        "valid": True,
        "IRI": doc.get("iri"),
        "ontologyId": doc.get("obo_id"),
        "label": doc.get("label"),
        "ontologyName": doc.get("ontology_name"),
        "matchType": match_type,
        "score": score,
        "synonyms": synonyms,
    }

def empty_ontology_result(keyword, match_type=None, error=None):
    """
    Create a standard result for an invalid or unknown ontology.

    Args:
        keyword: Original keyword.
        match_type: Type of match attempted.
        error: Optional error message.

    Returns:
        Dictionary with empty ontology fields.
    """
    return {
        "keyword": keyword,
        "valid": False,
        "IRI": None,
        "ontologyId": None,
        "label": None,
        "ontologyName": None,
        "matchType": match_type,
        "score": None,
        "synonyms": [],
        "error": error,
    }

def cache_synonyms(result):
    """
    Store synonyms in the ontology cache.

    Args:
        result: Valid ontology result containing synonyms.
    """
    for synonym in result.get("synonyms", []):
        if synonym not in ontology_cache:
            ontology_cache[synonym] = result
