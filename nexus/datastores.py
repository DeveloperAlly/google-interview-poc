"""Create the Agent Search data stores and the search app, then read each back and diff it against the spec.

Idempotent: an existing data store or engine is read back, never recreated or modified.
Chunking settings are permanent once created (Gate G2).
"""
import argparse, json, sys
import google.auth, google.auth.transport.requests, requests

API = "https://discoveryengine.googleapis.com/v1"
DS_SPEC = {
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "CONTENT_REQUIRED",
    "documentProcessingConfig": {
        "chunkingConfig": {"layoutBasedChunkingConfig": {"chunkSize": 500, "includeAncestorHeadings": True}},
        "defaultParsingConfig": {"layoutParsingConfig": {}},
    },
}
# Digital parser, no chunking. "The digital parser is offered without charge"; the layout parser that chunking
# needs is USD 10 per 1,000 pages (HTML page = 3,000 chars), about USD 504 for the full corpus. See DECISIONS D4.
DS_SPEC_LITE = {k: v for k, v in DS_SPEC.items() if k != "documentProcessingConfig"}


class Client:
    def __init__(self, project):
        self.project = project
        self.creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self.base = f"{API}/projects/{project}/locations/global/collections/default_collection"

    def call(self, method, url, **kw):
        if not self.creds.valid:
            self.creds.refresh(google.auth.transport.requests.Request())
        h = {"Authorization": f"Bearer {self.creds.token}", "X-Goog-User-Project": self.project,
             "Content-Type": "application/json"}
        import time
        for attempt in range(6):  # transient network errors (connection reset, chunked read) are retried with backoff
            try:
                return requests.request(method, url if url.startswith("http") else f"{API}/{url}", headers=h, timeout=120, **kw)
            except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.Timeout):
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt * 2)

    def wait(self, op):
        import time
        while not op.get("done"):
            time.sleep(5)
            op = self.call("GET", op["name"]).json()
        if "error" in op:
            sys.exit(f"FAIL operation {op['name']}: {op['error']}")
        return op


def diff(spec, got, path=""):
    out = []
    for k, v in spec.items():
        if isinstance(v, dict):
            out += diff(v, got.get(k, {}) or {}, f"{path}{k}.")
        elif got.get(k) != v:
            out.append(f"{path}{k}: want {v!r} got {got.get(k)!r}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--stores", default="ds-code,ds-prs")
    ap.add_argument("--engine", default="nexus-search")
    ap.add_argument("--profile", choices=["chunked", "lite"], default="lite")
    a = ap.parse_args()
    c = Client(a.project)
    spec = DS_SPEC if a.profile == "chunked" else DS_SPEC_LITE
    ok = True
    for ds in a.stores.split(","):
        r = c.call("GET", f"{c.base}/dataStores/{ds}")
        if r.status_code == 404:
            r = c.call("POST", f"{c.base}/dataStores?dataStoreId={ds}", json={"displayName": ds, **spec})
            print(f"create {ds}: HTTP {r.status_code}")
            if r.status_code != 200:
                sys.exit(f"FAIL create {ds}: {r.text[:500]}")
            c.wait(r.json())
            r = c.call("GET", f"{c.base}/dataStores/{ds}")
        print(f"get {ds}: HTTP {r.status_code}")
        d = diff(spec, r.json())
        got_dpc = r.json().get("documentProcessingConfig", {})
        if a.profile == "lite" and "chunkingConfig" in got_dpc:
            d.append("lite store has chunking enabled")
        print(f"  config diff vs spec: {d or 'none'}")
        ok &= not d
    # lite: no add-ons, so every query stays inside the free allowance that "excludes Advanced Generative Answers"
    engine_cfg = ({"searchTier": "SEARCH_TIER_ENTERPRISE", "searchAddOns": ["SEARCH_ADD_ON_LLM"]} if a.profile == "chunked"
                  else {"searchTier": "SEARCH_TIER_ENTERPRISE"})
    r = c.call("GET", f"{c.base}/engines/{a.engine}")
    if r.status_code == 404:
        body = {"displayName": "Nexus", "dataStoreIds": a.stores.split(","), "solutionType": "SOLUTION_TYPE_SEARCH",
                "industryVertical": "GENERIC",
                "searchEngineConfig": engine_cfg}
        r = c.call("POST", f"{c.base}/engines?engineId={a.engine}", json=body)
        print(f"create engine {a.engine}: HTTP {r.status_code}")
        if r.status_code != 200:
            sys.exit(f"FAIL create engine: {r.text[:500]}")
        c.wait(r.json())
        r = c.call("GET", f"{c.base}/engines/{a.engine}")
    e = r.json()
    print(f"get engine {a.engine}: HTTP {r.status_code} stores={e.get('dataStoreIds')} tier={e.get('searchEngineConfig')}")
    if sorted(e.get("dataStoreIds", [])) != sorted(a.stores.split(",")):
        print(f"  engine data store diff: want {sorted(a.stores.split(','))} got {sorted(e.get('dataStoreIds', []))}")
        ok = False
    got = e.get("searchEngineConfig", {})
    if got.get("searchTier") != engine_cfg["searchTier"] or got.get("searchAddOns", []) != engine_cfg.get("searchAddOns", []):
        print(f"  engine config diff vs spec: want {engine_cfg} got {got}")
        ok = False
    if not ok:
        sys.exit("FAIL: a data store or engine config differs from spec")


if __name__ == "__main__":
    main()
