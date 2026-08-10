from urllib.parse import quote

from api_client import api_get_json
from config import HGNC_BASE_URL, HGNC_MAX_REQUESTS_PER_SECOND


gene_cache = {}


def validate_gene_code(gene_code):
    """
    Validate a gene symbol against HGNC.

    Strategy:
        1. Approved HGNC symbol
        2. Previous HGNC symbol: For clinical notes with outdated gene symbols
        3. Alias HGNC symbol: Clinical notes containing synonym or alternative symbols
        4. Search symbol function as fallback, in case the other functions don't work

    Args:
        gene_code: Gene symbol extracted from the structured output.

    Returns:
        Dictionary with gene validation result and HGNC information.
    """

    # If gene already found, retrieve the info from the cache
    if gene_code in gene_cache:
        return gene_cache[gene_code]

    if gene_code == "":
        result = empty_gene_result(gene_code, error="Empty gene code")
        gene_cache[gene_code] = result
        return result

    min_interval = 1 / HGNC_MAX_REQUESTS_PER_SECOND

    result = fetch_hgnc(field="symbol", value=gene_code, match_type="approved_symbol", min_interval=min_interval)
    if result["valid"]:
        gene_cache[gene_code] = result
        return result

    result = fetch_hgnc(field="prev_symbol", value=gene_code, match_type="previous_symbol", min_interval=min_interval)
    if result["valid"]:
        gene_cache[gene_code] = result
        return result

    result = fetch_hgnc(field="alias_symbol", value=gene_code, match_type="alias_symbol", min_interval=min_interval)
    if result["valid"]:
        gene_cache[gene_code] = result
        return result

    result = search_hgnc_symbol(gene_code, min_interval=min_interval)
    gene_cache[gene_code] = result
    return result


def fetch_hgnc(field, value, match_type, min_interval):
    """
    Query the HGNC fetch endpoint for a specific field and value.

    Args:
        field: HGNC field to query. Example: "symbol", "prev_symbol", "alias_symbol"
        value: Gene code to search for.
        match_type: Label describing the type of match attempted.
        min_interval: Minimum number of seconds to wait between HGNC requests.

    Returns:
        Dictionary with the HGNC validation result.

    """
    url = f"{HGNC_BASE_URL}/fetch/{field}/{quote(value)}"
    response = api_get_json(url, min_interval_seconds=min_interval)

    if response is None:
        return empty_gene_result(value, match_type=match_type, error="HGNC API request failed")

    docs = response.get("response", {}).get("docs", [])
    if len(docs) == 0:
        return empty_gene_result(value, match_type=match_type)

    return gene_result_from_hgnc_doc(value, docs[0], match_type)


def search_hgnc_symbol(value, min_interval):
    """
    Query the HGNC search endpoint for a specific field and value.
    This function is used as fallback when the gene code is not found in the fetch endpoint.
    It can return less exact matches than the fetch endpoint, so it is used only at the end.

    Args:
        value: Gene code to search for.
        min_interval: Minimum number of seconds to wait between HGNC requests.

    Returns:
        Dictionary with the HGNC validation result.
    """
    url = f"{HGNC_BASE_URL}/search/symbol/{quote(value)}"
    response = api_get_json(url, min_interval_seconds=min_interval)

    if response is None:
        return empty_gene_result(value, match_type="search_symbol", error="HGNC API request failed")

    docs = response.get("response", {}).get("docs", [])
    if len(docs) == 0:
        return empty_gene_result(value, match_type="not_found")

    return gene_result_from_hgnc_doc(value, docs[0], "search_symbol")


def gene_result_from_hgnc_doc(input_gene, doc, match_type):
    """
    Convert one HGNC API document into the standard output dictionary.

    Args:
        input_gene: Original gene code provided by the user or extracted from
                    the clinical note.
        doc: One document returned by the HGNC API.
        match_type: Type of match that found this document.

    Returns:
        Dictionary containing the standardized validated gene information.
    """

    return {
        "gene": input_gene,
        "valid": True,
        "HGNCId": doc.get("hgnc_id"),
        "approvedSymbol": doc.get("symbol"),
        "geneName": doc.get("name"),
        "status": doc.get("status"),
        "matchType": match_type,
    }


def empty_gene_result(gene_code, match_type=None, error=None):
    """
    Create a standard output dictionary for an invalid or unknown gene.

    Args:
        gene_code: Original gene code provided by the user or extracted from
                   the clinical note.
        match_type: Type of match that was attempted.
        error: Optional error message.

    Returns:
        Dictionary containing a standardized invalid gene result.
    """

    return {
        "gene": gene_code,
        "valid": False,
        "HGNCId": None,
        "approvedSymbol": None,
        "geneName": None,
        "status": None,
        "matchType": match_type,
        "error": error,
    }