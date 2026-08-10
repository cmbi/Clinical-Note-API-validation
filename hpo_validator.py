from api_client import api_get_json
from config import OLS4_BASE_URL, OLS_LLM_MIN_SCORE


symptom_cache = {}


def retrieve_hpo_id(symptom, use_llm_fallback=True):
    """
    Retrieve an HPO ontology mapping for a symptom.

    Strategy:
        1. Exact OLS search on HPO label and synonyms.
        2. If not found, optional OLS LLM semantic search.

    Args:
        symptom: String with the symptom

    Returns:
        Dictionary with the mapping result.
    """

    if symptom in symptom_cache:
        return symptom_cache[symptom]

    if symptom == "":
        result = _empty_symptom_result(symptom, error="Empty symptom")
        symptom_cache[symptom] = result
        return result

    exact_result = _exact_hpo_search(symptom)

    if exact_result["valid"] or not use_llm_fallback:
        symptom_cache[symptom] = exact_result
        _cache_synonyms(exact_result)
        return exact_result

    llm_result = _llm_hpo_search(symptom)

    if llm_result["valid"]:
        symptom_cache[symptom] = llm_result
        _cache_synonyms(llm_result)
        return llm_result

    symptom_cache[symptom] = exact_result
    return exact_result


def _exact_hpo_search(symptom):
    url = f"{OLS4_BASE_URL}/search"
    params = {
        "q": symptom,
        "ontology": "hp",
        "exact": "true",
        "obsoletes": "false",
        "fieldList": "iri,label,ontology_name,synonym,short_form,obo_id",
        "queryFields": "label,synonym",
    }

    response = api_get_json(url, params=params)

    if response is None:
        return _empty_symptom_result(symptom, match_type="exact_search", error="OLS API request failed")

    docs = response.get("response", {}).get("docs", [])

    if len(docs) == 0:
        return _empty_symptom_result(symptom, match_type="not_found")

    return _symptom_result_from_ols_doc(symptom, docs[0], match_type="exact_label_or_synonym")


def _llm_hpo_search(symptom):
    url = f"{OLS4_BASE_URL}/v2/ontologies/hp/classes/llm_search"
    params = {
        "q": symptom,
        "page": 0,
        "size": 1,
        "lang": "en",
        "model": "llama-embed-nemotron-8b_pca512",
        "isDefiningOntology": "false",
        "includeCurations": "true",
    }

    response = api_get_json(url, params=params)

    if response is None:
        return _empty_symptom_result(symptom, match_type="llm_search", error="OLS LLM search request failed")

    elements = response.get("elements", [])

    if len(elements) == 0:
        return _empty_symptom_result(symptom, match_type="llm_not_found")

    hit = elements[0]
    score = _safe_float(hit.get("score"))

    if score is None or score < OLS_LLM_MIN_SCORE:
        result = _empty_symptom_result(symptom, match_type="llm_below_threshold")
        result["score"] = score
        result["raw"] = hit
        return result

    return _symptom_result_from_ols_doc(
        symptom,
        hit,
        match_type="llm_semantic",
        score=score,
    )


def _symptom_result_from_ols_doc(input_symptom, doc, match_type, score=None):
    iri = doc.get("iri")
    hpo_id = doc.get("obo_id") or _iri_to_hpo_id(iri)
    synonyms = doc.get("synonym", [])

    if synonyms is None:
        synonyms = []
    elif not isinstance(synonyms, list):
        synonyms = [str(synonyms)]

    return {
        "symptom": input_symptom,
        "valid": True,
        "IRI": iri,
        "HPOId": hpo_id,
        "label": doc.get("label"),
        "ontologyName": doc.get("ontology_name"),
        "matchType": match_type,
        "score": score,
        "synonyms": synonyms,
        "raw": doc,
    }


def _empty_symptom_result(symptom, match_type=None, error=None):
    return {
        "symptom": symptom,
        "valid": False,
        "IRI": None,
        "HPOId": None,
        "label": None,
        "ontologyName": None,
        "matchType": match_type,
        "score": None,
        "synonyms": [],
        "error": error,
    }


def _iri_to_hpo_id(iri):
    if iri is None:
        return None

    last_part = iri.rstrip("/").split("/")[-1]

    if last_part.startswith("HP_"):
        return last_part.replace("HP_", "HP:")

    return last_part


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cache_synonyms(result):
    if not result.get("valid"):
        return

    for synonym in result.get("synonyms", []):
        if synonym not in symptom_cache:
            symptom_cache[synonym] = result
