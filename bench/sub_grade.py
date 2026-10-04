"""Grade MessageBoardAuditBench reports with the benchmark's own sheets, prompts and parsing, but through the
`claude` CLI on a subscription instead of a provider API (graph @aleph/prismql: the A/B of PrismQL for
slop-vestigators). Run from the benchmark checkout root:

  uv run python /path/to/sub_grade.py --out grades/ run_dir_or_report.md [...]

Per report: the 6 `v2` finding sheets (38 claims) and the `tldrh` holistic TL;DR sheet, each one `claude -p` call
with exactly `core.build_prompt`'s system + prefix + suffix. Writes <out>/<key>.json and prints
headline = 0.7 x mean(max(2s - 1, 0)) over claims + 0.3 x TL;DR, the benchmark's combined score.
Not comparable with published numbers (different judge path); comparable between arms graded the same way."""

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from messageboard_audit_bench.grading import core  # noqa: E402

CLAUDE = str(Path.home() / ".local/bin/claude")


def ask(model, effort, system, prompt):
    with tempfile.TemporaryDirectory() as cwd:
        cmd = [CLAUDE, "-p", "--model", model, "--effort", effort, "--system-prompt", system,
               "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers": {}}',
               "--setting-sources", "", "--no-session-persistence", "--output-format", "json"]
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(f"claude exited {r.returncode}: {r.stderr[-300:]}")
    return json.loads(r.stdout)["result"]


def grade_sheet(mode, rub, report_md, templates, model, effort):
    system, prefix, suffix = core.build_prompt(mode, rub["rubric_id"], report_md, templates)
    raw = ask(model, effort, system, prefix + suffix)
    data = core.extract_json(raw)
    if data is None:  # one retry, as the benchmark's own grader does
        data = core.extract_json(ask(model, effort, system, prefix + suffix + core.JSON_ONLY))
    if data is None:
        raise ValueError(f"{mode}/{rub['rubric_id']}: unparseable judge output")
    spec = core.MODES[mode]
    return rub["rubric_id"], core.parse_items(data, spec.lo, spec.hi)


def grade_report(key, report_md, model, effort, workers):
    out = {}
    for mode in ("v2", "tldrh"):
        sets, templates = core.load_sheets(mode)
        per_claim, per_rubric = {}, {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(grade_sheet, mode, rub, report_md, templates, model, effort) for rub in sets]
            for f in futs:
                rid, items = f.result()
                per_claim.update(items)
                per_rubric[rid] = {"score": round(sum(i["score"] for i in items.values()), 2), "max": len(items)}
        out[mode] = core.aggregate(key, key, f"claude-cli:{model}", mode, per_claim, per_rubric, sets)
    claims = [i["score"] for i in out["v2"]["scores"].values()]
    coverage = sum(max(2 * s - 1, 0) for s in claims) / len(claims)
    tldr = out["tldrh"]["accuracy"]
    out["headline"] = {"coverage_strict": round(coverage, 4), "tldr": tldr,
                       "combined": round(0.7 * coverage + 0.3 * tldr, 4), "n_claims": len(claims)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", help="run directories (work/report.md inside) or report .md files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="xhigh")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in a.reports:
        p = Path(r)
        md = p / "work" / "report.md" if p.is_dir() else p
        key = core.sanitise(p.name if p.is_dir() else p.stem)
        dst = out_dir / f"{key}.json"
        if dst.exists():
            print(f"{key}: already graded", flush=True)
            continue
        g = grade_report(key, md.read_text(), a.model, a.effort, a.workers)
        dst.write_text(json.dumps(g, indent=1, ensure_ascii=False))
        print(f"{key}: {g['headline']}", flush=True)


if __name__ == "__main__":
    main()
