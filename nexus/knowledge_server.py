"""Local page for querying both RAG stores side by side: http://127.0.0.1:8766/  (localhost only)."""
from __future__ import annotations
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import knowledge

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nexus: two stores</title><style>
:root{--bg:#f6f7f8;--fg:#1b2228;--card:#fff;--line:#dde2e6;--muted:#667;--ev:#1a5fb4;--ref:#a0522d}
@media (prefers-color-scheme:dark){:root{--bg:#121416;--fg:#e4e7ea;--card:#1b1e21;--line:#2c3136;--muted:#9aa;--ev:#7fb0ff;--ref:#e3a37a}}
body{font:15px/1.5 system-ui;max-width:1200px;margin:0 auto;padding:16px;background:var(--bg);color:var(--fg)}
form{display:flex;gap:8px;flex-wrap:wrap}input[type=text]{flex:1;min-width:240px;padding:8px;font:inherit}
button{padding:8px 14px;font:inherit}.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:800px){.cols{grid-template-columns:1fr}}section{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:10px 0}
.m{color:var(--muted);font-size:12px}.ev{color:var(--ev)}.ref{color:var(--ref)}h2{font-size:16px;margin:4px 0}pre{white-space:pre-wrap;font:inherit}
</style></head><body>
<h1>Nexus: your evidence and Google's view</h1>
<p class="m">Left: your own work (evidence). Right: Google Next '26 talks and Google Cloud case studies (reference only, never your experience).</p>
<form id="f"><input id="q" type="text" placeholder="Ask a question, e.g. How would you secure a multi-agent system on Google Cloud?">
<label class="m">evidence: <select id="mc"><option value="">repos + work docs</option><option value="my-content">my-content repo only</option><option value="docs">Drive and Notion work docs only</option></select></label>
<label class="m"><input id="co" type="checkbox" checked> compose answer</label><button>Ask</button></form>
<section id="ans" hidden><h2>Composed answer</h2><pre id="a"></pre><div class="m" id="am"></div></section>
<div class="cols"><div><h2 class="ev">Evidence (your work)</h2><div id="ev"></div></div>
<div><h2 class="ref">Reference (Google)</h2><div id="ref"></div></div></div>
<script>
const $=id=>document.getElementById(id);
function card(x,tag,i){const s=document.createElement('section');const h=document.createElement('div');
h.innerHTML='<b></b> <span class="m"></span>';h.querySelector('b').textContent=tag+(i+1)+' '+x.title;
h.querySelector('span').textContent=[x.kind,x.owner&&x.repo?x.owner+'/'+x.repo:x.event,x.path].filter(Boolean).join(' | ');
const p=document.createElement('div');p.className='m';p.textContent=x.snippet||'';s.append(h,p);
if(x.url&&/^https:\\/\\//.test(x.url)){const a=document.createElement('a');a.href=x.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='open';s.append(a)}return s}
$('f').addEventListener('submit',async e=>{e.preventDefault();const q=$('q').value.trim();if(!q)return;
$('ev').textContent='Searching...';$('ref').textContent='';$('ans').hidden=true;
try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({question:q,repo:$('mc').value||null,compose:$('co').checked})});const d=await r.json();
if(!r.ok)throw new Error(d.error||r.status);$('ev').textContent='';$('ref').textContent='';
d.evidence.forEach((x,i)=>$('ev').append(card(x,'E',i)));d.reference.forEach((x,i)=>$('ref').append(card(x,'G',i)));
if(!d.evidence.length)$('ev').textContent='No evidence found.';
if(d.composed){$('ans').hidden=false;$('a').textContent=d.composed.answer||('Error: '+d.composed.error);
$('am').textContent='Evidence used: '+(d.composed.evidence_used||[]).join(', ')+' | Reference used: '+(d.composed.reference_used||[]).join(', ')+((d.composed.gaps||[]).length?' | Gaps: '+d.composed.gaps.join('; '):'')+' | '+d.seconds+' s'}
}catch(err){$('ev').textContent='Error: '+err.message}});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/api/ask":
            return self._send(404, b'{"error":"not found"}')
        try:
            n = max(0, int(self.headers.get("Content-Length", "0") or 0))
            req = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
            q = str(req.get("question", "")).strip()[:1000]
            if not q:
                return self._send(400, b'{"error":"empty question"}')
            repo = req.get("repo") if req.get("repo") in ("my-content", "drive", "docs") else None
            out = knowledge.ask(q, evidence_repo=repo, compose_answer=bool(req.get("compose", True)))
            self._send(200, json.dumps(out).encode())
        except Exception as e:
            self._send(502, json.dumps({"error": str(e)[:400]}).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), H).serve_forever()
