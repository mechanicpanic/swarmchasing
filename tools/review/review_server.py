"""Review queue for PrismQL findings: a human marks each result group (or each
claim) true / false / unsure, with a note, and every verdict is kept.

Two kinds of queue:
- **query**: a PrismQL query on a running server; each result group is an item
  (events, why each matched, what each $variable stood for).
- **claims**: a JSONL of claims (the lead format: hook, when, agents, example);
  each item shows the claim and finds the quoted message in the corpus, with
  the events around it, plus a search box over that time window.

Run:  make review (from the repo root), or: uv run --project <prismql checkout> python review_server.py [--port 8960]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import tomllib
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

HERE = Path(__file__).resolve().parent
QUEUES = HERE / "queues"
VERDICTS = HERE / "verdicts.jsonl"
CLIENT = "review-page"

# name -> (base url, prismql.toml that server runs). Default: one server, PRISMQL_URL (this repo's :8931) with
# PRISMQL_CONFIG (this repo's prismql.toml). REVIEW_SERVERS='{"name": ["url", "path/to/prismql.toml"], ...}' replaces it.
if os.environ.get("REVIEW_SERVERS"):
    SERVERS: dict[str, tuple[str, Path]] = {k: (u, Path(c).expanduser()) for k, (u, c) in json.loads(os.environ["REVIEW_SERVERS"]).items()}
else:
    SERVERS = {"local": (os.environ.get("PRISMQL_URL", "http://127.0.0.1:8931"),
                         Path(os.environ.get("PRISMQL_CONFIG", HERE.parent.parent / "prismql.toml")))}
PAGE = 50  # the servers' max_results


def _http(method: str, url: str, body: dict | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Content-Type": "application/json", "X-PrismQL-Client": CLIENT})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            raise HTTPException(e.code, str(e)) from e


def _base(server: str) -> str:
    if server not in SERVERS:
        raise HTTPException(404, f"unknown server {server}")
    return SERVERS[server][0]


def _parquet(server: str, corpus: str) -> Path:
    toml_path = SERVERS[server][1]
    cfg = tomllib.loads(toml_path.read_text())
    data = cfg.get("corpora", {}).get(corpus, {}).get("data")
    if not data:
        raise HTTPException(404, f"no data path for {server}/{corpus}")
    p = Path(data)
    return p if p.is_absolute() else (toml_path.parent / p).resolve()


def _save(q: dict) -> None:
    QUEUES.mkdir(exist_ok=True)
    (QUEUES / f"{q['id']}.json").write_text(json.dumps(q))


def _load(qid: str) -> dict:
    f = QUEUES / f"{qid}.json"
    if not f.exists():
        raise HTTPException(404, "no such queue")
    return json.loads(f.read_text())


def _verdicts() -> dict[tuple[str, str], dict]:
    """Latest verdict per (queue, item)."""
    out: dict[tuple[str, str], dict] = {}
    if VERDICTS.exists():
        for line in VERDICTS.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                out[(v["queue"], v["item"])] = v
    return out


def _tally(q: dict, verdicts: dict) -> dict:
    t = {"yes": 0, "no": 0, "unsure": 0, "todo": 0}
    for it in q["items"]:
        v = verdicts.get((q["id"], it["key"]))
        t[v["verdict"] if v else "todo"] += 1
    judged = t["yes"] + t["no"]
    t["precision"] = round(t["yes"] / judged, 3) if judged else None
    return t


app = FastAPI()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HERE / "review.html")


@app.get("/trails")
def trails_page() -> FileResponse:
    return FileResponse(HERE / "trails.html")


@app.get("/api/servers")
def servers() -> dict:
    out = {}
    for name, (base, _) in SERVERS.items():
        try:
            out[name] = _http("GET", f"{base}/corpora")["corpora"]
        except Exception:
            out[name] = None
    return out


@app.post("/api/queues")
def create_query_queue(body: dict) -> dict:
    server, corpus, query = body["server"], body["corpus"], body["query"]
    limit = int(body.get("limit") or 50)
    req = {"corpus": corpus, "query": query, "max_results": PAGE, "explain": True}
    if body.get("dictionaries"):
        req["dictionaries"] = body["dictionaries"]
    first = _http("POST", f"{_base(server)}/evaluate", req)
    if not first.get("ok", True) or "results" not in first:
        raise HTTPException(422, json.dumps(first.get("error") or first)[:500])
    groups = list(first["results"])
    rid = first.get("result_id")
    while rid and len(groups) < min(limit, first.get("total", 0)):
        page = _http("GET", f"{_base(server)}/results/{rid}?offset={len(groups)}&limit={PAGE}&explain=true")
        if not page.get("results"):
            break
        groups += page["results"]
    items = [{"key": "|".join(map(str, g["ids"])), "group": g} for g in groups[:limit]]
    q = {"id": uuid.uuid4().hex[:8], "name": body.get("name") or query[:60], "mode": "query",
         "server": server, "corpus": corpus, "query": query, "total": first.get("total"),
         "result_id": rid, "created": time.time(), "items": items}
    _save(q)
    return {"id": q["id"], "items": len(items), "total": q["total"]}


@app.post("/api/queues/claims")
def create_claims_queue(body: dict) -> dict:
    path = Path(body["path"]).expanduser()
    claims = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if body.get("ids"):
        want = set(body["ids"])
        claims = [c for c in claims if c.get("id") in want]
    items = [{"key": str(c.get("id") or i), "claim": c} for i, c in enumerate(claims)]
    q = {"id": uuid.uuid4().hex[:8], "name": body.get("name") or path.stem, "mode": "claims",
         "server": body.get("server", next(iter(SERVERS))), "corpus": body.get("corpus", "village"),
         "source": str(path), "created": time.time(), "items": items}
    _save(q)
    return {"id": q["id"], "items": len(items)}


@app.get("/api/queues")
def list_queues() -> list[dict]:
    v = _verdicts()
    out = []
    for f in sorted(QUEUES.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        q = json.loads(f.read_text())
        out.append({k: q.get(k) for k in ("id", "name", "mode", "server", "corpus", "query", "total")}
                   | {"n": len(q["items"]), "tally": _tally(q, v)})
    return out


@app.get("/api/queues/{qid}")
def get_queue(qid: str) -> dict:
    q = _load(qid)
    v = _verdicts()
    for it in q["items"]:
        it["verdict"] = v.get((qid, it["key"]))
    q["tally"] = _tally(q, v)
    return q


@app.post("/api/verdicts")
def add_verdict(body: dict) -> dict:
    if body.get("verdict") not in ("yes", "no", "unsure", "clear"):
        raise HTTPException(422, "verdict must be yes, no, unsure or clear")
    rec = {"queue": body["queue"], "item": body["item"], "verdict": body["verdict"],
           "note": body.get("note", ""), "reviewer": body.get("reviewer", ""),
           "at": datetime.now().isoformat(timespec="seconds")}
    with VERDICTS.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return {"ok": True}


@app.get("/api/context")
def context(server: str, corpus: str, id: str, before: int = 8, after: int = 8) -> Any:  # noqa: A002
    qs = urllib.parse.urlencode({"corpus": corpus, "id": id, "before": before, "after": after})
    return _http("GET", f"{_base(server)}/context?{qs}")


def _window(when: str) -> tuple[datetime, datetime] | None:
    days = re.findall(r"20\d\d-\d\d-\d\d", str(when))
    if not days:
        return None
    ds = sorted(datetime.fromisoformat(d) for d in days)
    return ds[0] - timedelta(days=1), ds[-1] + timedelta(days=2)


def _quote(example: str) -> str:
    """The most findable piece of a lead's example: its longest quoted span."""
    spans = re.findall(r"[\"“'‘]([^\"”'’]{15,})[\"”'’]", example or "")
    s = max(spans, key=len) if spans else (example or "")
    s = re.sub(r"\s+", " ", s.replace("…", " ").replace("...", " ")).strip()
    return s[:60]


def _search_parquet(server: str, corpus: str, text: str, start: datetime | None,
                    end: datetime | None, agent: str | None, limit: int = 50) -> list[dict]:
    lf = pl.scan_parquet(_parquet(server, corpus))
    cols = lf.collect_schema().names()
    tcol = "time" if "time" in cols else None
    if tcol and start is not None and end is not None:
        lf = lf.filter(pl.col(tcol).is_between(pl.lit(start).dt.replace_time_zone("UTC"),
                                               pl.lit(end).dt.replace_time_zone("UTC")))
    if agent and "agent" in cols:
        lf = lf.filter(pl.col("agent") == agent)
    if text:
        lf = lf.filter(pl.col("text").str.to_lowercase().str.contains(text.lower(), literal=True))
    keep = [c for c in ("id", "time", "kind", "agent", "actor", "room", "text") if c in cols]
    df = lf.select(keep).head(limit).collect()
    return [{k: (str(v) if k == "time" else v) for k, v in r.items()} for r in df.to_dicts()]


@app.get("/api/claim_evidence")
def claim_evidence(qid: str, key: str) -> dict:
    q = _load(qid)
    item = next((it for it in q["items"] if it["key"] == key), None)
    if item is None:
        raise HTTPException(404, "no such item")
    c = item["claim"]
    win = _window(c.get("when", ""))
    quote = _quote(c.get("example", ""))
    hits = []
    if quote:
        hits = _search_parquet(q["server"], q["corpus"], quote, *(win or (None, None)), None, 20)
        if not hits and len(quote) > 30:
            hits = _search_parquet(q["server"], q["corpus"], quote[:30], *(win or (None, None)), None, 5)
    hits.sort(key=lambda h: h.get("kind") == "memory")  # a chat message beats a memory dump
    ctx = context(q["server"], q["corpus"], hits[0]["id"], 10, 10) if hits else None
    return {"quote": quote, "window": [str(w) for w in win] if win else None, "anchors": hits, "context": ctx}


@app.get("/api/claim_summary")
def claim_summary(qid: str, key: str) -> dict:
    """The dataset summary a claim disputes, as recorded by the agent that made the claim
    (summary_links.jsonl beside the claims file). No link recorded means none is shown."""
    q = _load(qid)
    links = Path(q.get("source", "")).with_name("summary_links.jsonl")
    if not links.exists():
        return {"status": "no_links_file"}
    for line in links.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            if d.get("id") == key:
                return {"status": "linked", **d}
    return {"status": "not_recorded"}


@app.get("/api/search")
def search(qid: str, text: str = "", agent: str = "", start: str = "", end: str = "") -> list[dict]:
    q = _load(qid)
    s = datetime.fromisoformat(start) if start else None
    e = datetime.fromisoformat(end) if end else None
    return _search_parquet(q["server"], q["corpus"], text, s, e, agent or None, 60)


TRAILS = HERE / "trails.jsonl"


def _steps() -> dict[str, dict]:
    """Latest version of every trail step (the file is append-only)."""
    out: dict[str, dict] = {}
    if TRAILS.exists():
        for line in TRAILS.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["id"]] = {**out.get(d["id"], {}), **d}
    return out


def _write_step(d: dict) -> None:
    with TRAILS.open("a") as fh:
        fh.write(json.dumps(d) + "\n")


@app.get("/api/trails")
def trails() -> dict:
    """Every trail with its steps; each step carries its review tally when it has a queue."""
    v = _verdicts()
    by: dict[str, list] = {}
    for st in _steps().values():
        if st.get("deleted"):
            continue
        if st.get("queue"):
            try:
                st["tally"] = _tally(_load(st["queue"]), v)
            except HTTPException:
                pass
        by.setdefault(st["trail"], []).append(st)
    for steps in by.values():
        steps.sort(key=lambda s: s["at"])
    return by


@app.post("/api/steps")
def add_step(body: dict) -> dict:
    """A step: the question in words, what it follows up on, and either a PrismQL query
    (run now: total recorded; optionally a review queue) or a note for work done elsewhere."""
    st = {"id": uuid.uuid4().hex[:8], "trail": body["trail"], "question": body["question"],
          "parent": body.get("parent") or None, "kind": body.get("kind", "query"),
          "author": body.get("author", ""), "at": datetime.now().isoformat(timespec="seconds"),
          "conclusion": body.get("conclusion", ""), "note": body.get("note", "")}
    if st["kind"] == "query":
        st |= {"server": body["server"], "corpus": body["corpus"], "query": body["query"]}
        if body.get("review"):
            q = create_query_queue({"server": body["server"], "corpus": body["corpus"], "query": body["query"],
                                    "name": body["question"][:80], "limit": body.get("limit", 30)})
            st |= {"queue": q["id"], "total": q["total"]}
        else:
            res = _http("POST", f"{_base(body['server'])}/evaluate",
                        {"corpus": body["corpus"], "query": body["query"], "max_results": 1})
            if res.get("ok") is False or "error" in res:
                raise HTTPException(422, json.dumps(res.get("error"))[:400])
            st["total"] = res.get("total")
            st["result_id"] = res.get("result_id")
    _write_step(st)
    return st


@app.post("/api/steps/{sid}")
def update_step(sid: str, body: dict) -> dict:
    if sid not in _steps():
        raise HTTPException(404, "no such step")
    if body.get("parent") == sid:
        raise HTTPException(422, "a step can't follow up on itself")
    upd = {"id": sid, **{k: body[k] for k in ("conclusion", "question", "note", "parent", "deleted") if k in body}}
    _write_step(upd)
    return _steps()[sid]


@app.get("/api/export/{qid}", response_class=PlainTextResponse)
def export(qid: str) -> str:
    q = get_queue(qid)
    t = q["tally"]
    lines = [f"# Review: {q['name']}", "",
             f"- mode: {q['mode']} · server/corpus: {q['server']}/{q['corpus']}"]
    if q["mode"] == "query":
        lines.append(f"- query: `{q['query']}` (total groups {q.get('total')}; reviewed sample {len(q['items'])})")
    lines += [f"- verdicts: ✔ {t['yes']} · ✘ {t['no']} · ? {t['unsure']} · not yet {t['todo']}"
              + (f" · precision {t['precision']:.0%}" if t["precision"] is not None else ""), ""]
    for it in q["items"]:
        v = it.get("verdict") or {}
        mark = {"yes": "✔", "no": "✘", "unsure": "?"}.get(v.get("verdict"), "·")
        label = it["claim"].get("hook", "")[:140] if q["mode"] == "claims" else it["key"][:80]
        lines.append(f"- {mark} `{it['key']}` {label}" + (f" — {v['note']}" if v.get("note") else ""))
    return "\n".join(lines) + "\n"


@app.get("/api/trails/export", response_class=PlainTextResponse)
def export_trail(name: str) -> str:
    """One trail as nested markdown: question, query or note, size, verdicts, conclusion."""
    steps = trails().get(name)
    if not steps:
        raise HTTPException(404, "no such trail")
    ids = {s["id"] for s in steps}
    kids: dict[str | None, list] = {}
    for s in steps:
        kids.setdefault(s.get("parent") if s.get("parent") in ids else None, []).append(s)
    lines = [f"# Trail: {name}", "", "Each step: the question, what was run or read, and the conclusion.",
             "Indented steps follow up on the step above them.", ""]

    def walk(pid: str | None, depth: int) -> None:
        for s in kids.get(pid, []):
            ind = "  " * depth
            lines.append(f"{ind}- **{s['question']}**" + (f" _({s['author']}, {s['at'][:16]})_" if s.get("author") else f" _({s['at'][:16]})_"))
            if s.get("query"):
                lines.append(f"{ind}  - query on `{s.get('server')}/{s.get('corpus')}`: `{s['query']}` → {s.get('total')} groups")
            if s.get("tally"):
                t = s["tally"]
                lines.append(f"{ind}  - review: ✔ {t['yes']} · ✘ {t['no']} · ? {t['unsure']} · not yet {t['todo']}")
            if s.get("note"):
                lines.append(f"{ind}  - note: {s['note']}")
            lines.append(f"{ind}  - **conclusion:** {s.get('conclusion') or '_open_'}")
            walk(s["id"], depth + 1)

    walk(None, 0)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8960)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")
