"""Auto-generated API stub from deltasci discover-api.
Source page: https://marco.igen.org.br/
Identified endpoint: POST https://marco.igen.org.br/api/correlation-matrix
Score: 11.00  (same-origin, path:/api/, path:/correlation, json-379804B, POST-with-payload, 200-OK)

NOTE: this is a starting point. Verify the parameter names + types
against endpoints.json and the live API before using at scale.
"""

import requests

BASE_URL = 'https://marco.igen.org.br'
ENDPOINT_PATH = '/api/correlation-matrix'

def call_api(**params) -> dict:
    """Call the discovered POST endpoint.

    Sample payload structure (as captured):
    {
        "manufacturer_kit": "All_Manufacturers_Kits",
        "locus_group": "A"
    }
    """
    payload = {**{"manufacturer_kit": "All_Manufacturers_Kits", "locus_group": "A"}, **params}
    r = requests.post(BASE_URL + ENDPOINT_PATH, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    # Sanity check — confirm the endpoint resolves and returns JSON.
    sample = call_api()
    import json as _json
    print(_json.dumps(sample, indent=2)[:1000])

# --- Other candidate endpoints (from endpoints.json) ---
#   9.50  POST https://marco.igen.org.br/api/analyze
#   8.00  GET https://marco.igen.org.br/api/options
