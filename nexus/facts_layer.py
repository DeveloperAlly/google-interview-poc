"""Facts layer (issue #21): turn raw code into cited, plain-language facts the answer path can use.

Build:  python3 facts_layer.py            -> writes state/facts.json
Use:    facts_for(question) -> list of evidence dicts (kind "fact") for the composer.

Deterministic: ripgrep signatures over every cloned repo (CI, IaC, deploy scripts, manifests, code), one fact per
(repo, technology) with up to 3 file:line citations and commit permalinks. Lilypad-Tech facts carry her_role
"directed" (owner instruction, 23 Oct 14:05: her startup's work, built by her team under her direction);
DeveloperAlly facts carry "built". Third-party library internals (vendored LiteLLM provider code, docs sites,
node_modules) are skipped so they do not masquerade as company decisions.
"""
from __future__ import annotations
import json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLONES = ROOT / "state" / "clones"
OUT = ROOT / "state" / "facts.json"
# Private repo names never enter the public repo: exclusions live in gitignored state.
# {"exclude_repos": [...], "library_forks": [...]}
_EXP = ROOT / "state" / "answer-exclusions.json"
_EX = {"exclude_repos": [], "library_forks": [], **(json.loads(_EXP.read_text()) if _EXP.exists() else {})}

TECH = {
    "Google Cloud": r"\bgcloud\b|gcr\.io|pkg\.dev|provider\s+\"google\"|google-github-actions|GOOGLE_APPLICATION_CREDENTIALS|\bgsutil\b|storage\.googleapis\.com|compute\.googleapis|\bGKE\b|Cloud Run",
    "Gemini / Vertex AI": r"\bgemini\b|vertexai|aiplatform\.googleapis|google-genai|google\.generativeai",
    "LangGraph": r"langgraph|create_react_agent",
    "LangChain": r"\blangchain\b|langchain_",
    "LlamaIndex": r"llama_index|llamaindex",
    "Autonolas (Olas) agents": r"autonolas|open-autonomy|\bolas\b",
    "Model Context Protocol (MCP)": r"modelcontextprotocol|mcp_servers|\bMCP\b",
    "LiteLLM gateway": r"\blitellm\b",
    "OpenAI-compatible API": r"/v1/chat/completions",
    "Kubernetes / Helm": r"\bkubectl\b|\bhelm\b|apiVersion:\s*apps/v1",
    "Terraform (IaC)": r"\bterraform\b|resource\s+\"[a-z_]+\"\s+\"",
    "AWS": r"amazonaws\.com|\bboto3\b|aws_access_key_id|\baws\s+s3\b",
    "Docker containers": r"^FROM\s+\S+",
    "Arbitrum / Solidity smart contracts": r"arbitrum|pragma solidity",
    "Kafka streaming": r"\bkafka\b",
    "Prometheus / Grafana / OpenTelemetry": r"prometheus|grafana|opentelemetry|\botel\b",
    "Cloudflare Workers": r"wrangler|cloudflare",
    "Supabase / Postgres": r"supabase|postgres",
    "n8n workflows": r"\bn8n\b",
    "Bacalhau compute": r"bacalhau",
    "Filecoin / FVM": r"\bfvm\b|filecoin",
    "GitHub Actions CI": r"^on:\s*$|runs-on:",
    "WireGuard VPN": r"wireguard|wg-quick",
    "Rust": r"^\[package\]",
}
SKIP = ["!**/node_modules/**", "!**/vendor/**", "!**/litellm/llms/**", "!**/docs/my-website/**", "!**/*.lock",
        "!**/package-lock.json", "!**/go.sum", "!**/*.min.js", "!**/*.svg", "!**/*.map", "!**/dist/**"]

# question words -> technologies to look up
ASK = [
    (r"google cloud|\bgcp\b|\bgke\b|cloud run|google('s)? (platform|services)", ["Google Cloud", "Gemini / Vertex AI"]),
    (r"gemini|vertex", ["Gemini / Vertex AI", "Google Cloud"]),
    (r"langgraph|orchestration framework|autogen|crewai|agent framework", ["LangGraph", "LangChain", "Autonolas (Olas) agents", "n8n workflows"]),
    (r"langchain|llamaindex", ["LangChain", "LlamaIndex", "LangGraph"]),
    (r"\bmcp\b|model context protocol|a2a", ["Model Context Protocol (MCP)"]),
    (r"kubernetes|k8s|helm|container", ["Kubernetes / Helm", "Docker containers"]),
    (r"terraform|infrastructure as code|\biac\b", ["Terraform (IaC)"]),
    (r"\baws\b|amazon", ["AWS"]),
    (r"observab|monitor|telemetry|metrics", ["Prometheus / Grafana / OpenTelemetry"]),
    (r"kafka|stream", ["Kafka streaming"]),
    (r"gateway|api integration|platform integration|failover|router|routing", ["LiteLLM gateway", "OpenAI-compatible API"]),
    (r"cloud[- ]native|cloud architecture|cloud infrastructure|deploy", ["Google Cloud", "Kubernetes / Helm", "Terraform (IaC)", "Docker containers", "GitHub Actions CI"]),
    (r"smart contract|blockchain|solidity|arbitrum", ["Arbitrum / Solidity smart contracts"]),
    (r"n8n|workflow automation", ["n8n workflows"]),
    (r"which languages|programming language|rust", ["Rust"]),
]


def _sha(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def build() -> list[dict]:
    facts = []
    for owner_dir in sorted(p for p in CLONES.iterdir() if p.is_dir()):
        for repo in sorted(p for p in owner_dir.iterdir() if p.is_dir()):
            sha = _sha(repo)
            for tech, pat in TECH.items():
                cmd = ["rg", "-n", "-i" if tech not in ("Docker containers", "Rust", "GitHub Actions CI") else "-s",
                       "--no-messages", "-m", "1", "-e", pat]
                for g in SKIP:
                    cmd += ["-g", g]
                if tech == "Docker containers":
                    cmd += ["-g", "**/Dockerfile*"]
                if tech == "Rust":
                    cmd += ["-g", "**/Cargo.toml"]
                if tech == "GitHub Actions CI":
                    cmd += ["-g", ".github/workflows/*"]
                cmd.append(".")
                r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
                hits = []
                for line in r.stdout.splitlines():
                    m = re.match(r"\./(.+?):(\d+):(.*)", line)
                    if not m:
                        continue
                    path, ln, snip = m.group(1), int(m.group(2)), m.group(3).strip()[:160]
                    hits.append({"path": path, "line": ln, "snippet": snip,
                                 "url": f"https://github.com/{owner_dir.name}/{repo.name}/blob/{sha}/{path}#L{ln}" if sha else ""})
                if hits:
                    # prefer CI / IaC / deploy / manifests over arbitrary source files
                    hits.sort(key=lambda h: (0 if re.search(r"(^|/)(\.github|\.circleci|ops|deploy|infra|docker|helm|terraform)|Dockerfile|\.tf$|\.ya?ml$|requirements|pyproject|package\.json|go\.mod|Cargo\.toml", h["path"]) else 1, h["path"]))
                    facts.append({"owner": owner_dir.name, "repo": repo.name, "tech": tech, "files": len(hits),
                                  "her_role": "directed" if owner_dir.name == "Lilypad-Tech" else "built",
                                  "cites": hits[:3]})
    OUT.write_text(json.dumps(facts, indent=1))
    return facts


_F = None


def facts_for(question: str, max_repos: int = 6) -> list[dict]:
    global _F
    if _F is None:
        _F = json.loads(OUT.read_text()) if OUT.exists() else []
    q = question.lower()
    techs = []
    for pat, ts in ASK:
        if re.search(pat, q):
            techs += [t for t in ts if t not in techs]
    out = []
    for t in techs[:4]:
        noise = re.compile(r"dist-info|cookbook/|\.ipynb$|/chats/|exports/|(^|/)index/|memories\.json|\.tsv$|/test/|research-evidence|TECH_OPTIONS|openapi\.yaml|studio\.yaml")
        rows = []
        for f in _F:
            if f["tech"] != t or f["repo"] in _EX["exclude_repos"]:
                continue
            cites = [c for c in f["cites"] if not noise.search(c["path"])]
            if f["repo"] in _EX["library_forks"]:  # library forks: keep the owner's own config, CI and tests, not library internals
                cites = [c for c in cites if re.match(r"(tests/|\.circleci/|anura_|config\.yaml|proxy_server_config|mcp_servers|deploy/|docker)", c["path"])]
            if cites:
                rows.append({**f, "cites": cites})
        if not rows:
            continue
        strong = re.compile(r"(^|/)(ops|deploy|infra|\.github|\.circleci|helm|terraform|docker)/|Dockerfile|README|\.tf$|tests/")
        rows.sort(key=lambda f: (f["owner"] != "Lilypad-Tech", not strong.search(f["cites"][0]["path"]), -f["files"]))
        lines = [f"FACTS FROM CODE: {t}. Extracted deterministically from the indexed repositories (file, line, commit permalink). "
                 f"Lilypad-Tech repos are her startup's work, built by her team under her direction (her_role: directed); "
                 f"DeveloperAlly repos are her own (her_role: built)."]
        for f in rows[:max_repos]:
            c = "; ".join(f"{x['path']} line {x['line']}: `{x['snippet']}` ({x['url']})" for x in f["cites"])
            lines.append(f"- {f['owner']}/{f['repo']} uses {t} (her_role: {f['her_role']}). Evidence: {c}")
        out.append({"kind": "fact", "repo": rows[0]["owner"] + "/" + rows[0]["repo"], "path": f"facts: {t}",
                    "url": rows[0]["cites"][0]["url"], "text": "\n".join(lines)})
    return out


if __name__ == "__main__":
    fs = build()
    print(len(fs), "facts")
    from collections import Counter
    print(Counter(f["tech"] for f in fs).most_common())
