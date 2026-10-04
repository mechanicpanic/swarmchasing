"""C9: open ballots herd? Every village vote whose ballots were cast as public chat messages, in order.
Inputs (committed, hand-labelled): votes.csv (one row per vote, with its announced result) and labels.csv (one row
per ballot: vote, first 8 hex of the message id, choice, ballot_type first|late|switch, cites_tally 0/1 by hand).
A ballot is the first chat message in which an agent states its choice (a declared lean counts; see the note column).
cites_tally = the ballot message, or the voter's THOUGHT rows for it (same id, or the voter's thoughts in the
10 minutes before it), refer to other agents' votes, the running count, or "the consensus". Coded by hand; the
regex column `auto` is a reading aid only and is printed, not trusted.
leader_at_time = the strict plurality of the choices standing before this ballot (each earlier voter's latest
public choice); "none" for the first ballot, "tie" when the top is shared. with_leader = choice == leader_at_time.
Order test (primary): within each contested vote the top choice is the most common first-ballot choice (votes with a
tied top are left out); the statistic is the summed position of the minority ballots, and the null permutes the
order of the vote's first ballots (n draws); p = P(null <= observed). Herding predicts minority ballots early,
before a leader forms. A remark-only count of ballots agreeing with a strict earlier leader is also printed; with
the multiset of first-ballot choices fixed it moves only through ties, so it is not a herding test.
V04 (approval, multi-choice) and switch rows are listed but kept out of the pooled numbers. Switch rows update the
standing choice of their agent (so later leaders see them); both shuffles use the non-switch ballots only.
usage (repo root): REPO=/path/to/main/checkout python runs/c9_ballots/c9.py [--n 10000] [--review]
  -> runs/c9_ballots/ballots.csv (ids and labels only) and the per-vote table on stdout"""
import argparse, csv, os, re
from collections import Counter
import numpy as np
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
VILLAGE = os.environ.get("VILLAGE", os.environ.get("REPO", ".") + "/data/village.parquet")
CITE = re.compile(r"(?i)(votes? (have|has) (already )?(been )?(cast|come in)|\b(\d+|one|two|three|four|five|six|seven|"
                  r"eight|nine|ten)\s+(votes|approvals|supporters)\b|tally|consensus|unanimous|landslide|majority|"
                  r"already voted|have voted|has voted|voted for|following .{0,25}lead|join(ing)? the|adding my vote|"
                  r"the village has|clear(ly)? (preference|mandate|winner)|effectively decided|momentum|convergence|"
                  r"as well!|aligned with the others|leading)")


def load_labels():
    votes = {r["vote"]: r for r in csv.DictReader(open(f"{HERE}/votes.csv"))}
    labels = list(csv.DictReader(open(f"{HERE}/labels.csv")))
    return votes, labels


def resolve(labels, votes):
    df = pl.read_parquet(VILLAGE, columns=["id", "time", "kind", "agent", "text"])
    talk = df.filter(pl.col("kind").is_in(["AGENT_TALK"]))
    rows = []
    for lb in labels:
        d = pl.lit(votes[lb["vote"]]["date"]).str.to_date()
        hit = talk.filter(pl.col("id").str.starts_with(lb["id8"]),
                          (pl.col("time").dt.date() - d).dt.total_days().abs() <= 1)
        assert hit.height == 1, (lb["vote"], lb["id8"], hit.height)
        r = hit.row(0, named=True)
        rows.append({**lb, "id": r["id"], "time": r["time"], "agent": r["agent"], "text": r["text"] or ""})
    th = df.filter(pl.col("kind") == "THOUGHT", pl.col("agent").is_in(list({r["agent"] for r in rows})))
    for r in rows:  # thoughts behind this ballot: same id, or the voter's thoughts in the 10 minutes before it
        t = th.filter(pl.col("agent") == r["agent"], (pl.col("id") == r["id"]) |
                      ((pl.col("time") <= r["time"]) & (pl.col("time") >= r["time"] - pl.duration(minutes=10))))
        r["thought"] = " ".join(t["text"].drop_nulls().to_list())
    return rows


def leader(standing):
    c = Counter(standing.values())
    if not c:
        return "none"
    top = c.most_common()
    return "tie" if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]


def annotate(rows):
    out = []
    for v in sorted({r["vote"] for r in rows}):
        vr = sorted([r for r in rows if r["vote"] == v], key=lambda r: r["time"])
        standing = {}
        for i, r in enumerate(vr, 1):
            prev = {a: c for a, c in standing.items() if a != r["agent"]}
            if v == "V04":  # approval: leader = top approval count; with_leader = approves it
                cnt = Counter(x for c in prev.values() for x in c.split(";"))
                best = max(cnt.values()) if cnt else 0
                tops = sorted(k for k, n in cnt.items() if n == best) if cnt else []
                r["leader_at_time"] = "none" if not tops else "|".join(tops)
                r["with_leader"] = "" if not tops else int(all(t in r["choice"].split(";") for t in tops))
            else:
                r["leader_at_time"] = leader(prev)
                r["with_leader"] = int(r["choice"] == r["leader_at_time"]) if r["leader_at_time"] not in ("none", "tie") else ""
            r["order"] = i
            standing[r["agent"]] = r["choice"]
            out.append(r)
    return out


def with_leader_count(seq):
    """seq: list of (agent, choice) in time order -> ballots agreeing with a strict earlier leader."""
    standing, k = {}, 0
    for a, c in seq:
        ld = leader({x: y for x, y in standing.items() if x != a})
        k += c == ld
        standing[a] = c
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--review", action="store_true", help="print the auto citation flag and its phrase per ballot")
    a = ap.parse_args()
    votes, labels = load_labels()
    rows = annotate(resolve(labels, votes))
    for r in rows:
        m = CITE.search(r["text"]) or CITE.search(r["thought"])
        r["auto"] = int(bool(m))
        if a.review:
            src = "msg" if CITE.search(r["text"]) else ("thought" if m else "-")
            ctx = (r["text"] if src == "msg" else r["thought"])
            s = ctx[max(0, m.start() - 70): m.end() + 50].replace("\n", " ") if m else ""
            print(f"{r['vote']} {r['order']:>2} {r['id'][:8]} {r['agent'][:22]:22s} {r['choice'][:22]:22s} "
                  f"lead={str(r['leader_at_time'])[:20]:20s} hand={r['cites_tally'] or '?'} auto={r['auto']} {src}: …{s}…")
    with open(f"{HERE}/ballots.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "time", "agent", "vote", "choice", "cites_tally", "leader_at_time", "with_leader",
                    "order", "ballot_type"])
        for r in rows:
            w.writerow([r["id"], r["time"].strftime("%Y-%m-%dT%H:%M:%SZ"), r["agent"], r["vote"], r["choice"],
                        r["cites_tally"], r["leader_at_time"], r["with_leader"], r["order"], r["ballot_type"]])
    # per-vote table
    print(f"\n{'vote':4} {'date':10} {'fam':8} {'n':>3} {'lead':>4} {'toLd':>5} {'cite':>5} {'1st=res':>7}  label")
    pool = []
    for v, meta in votes.items():
        vr = [r for r in rows if r["vote"] == v and r["ballot_type"] != "switch"]
        defined = [r for r in vr if r["with_leader"] != ""]
        k = sum(int(r["with_leader"]) for r in defined)
        cites = sum(int(r["cites_tally"] or 0) for r in vr)
        first = vr[0]["choice"]
        res = meta["result"]
        fm = "—" if v == "V04" else ("yes" if first == res or first.lstrip("#") == res.lstrip("#") else "no")
        print(f"{v:4} {meta['date']} {meta['family']:8} {len(vr):>3} {len(defined):>4} "
              f"{(f'{k}/{len(defined)}' if defined else '—'):>5} {cites:>2}/{len(vr):<2} {fm:>7}  {meta['label'][:60]}")
        if v != "V04":
            pool.append(vr)
    # pooled
    allb = [r for vr in pool for r in vr]
    d = [r for r in allb if r["with_leader"] != ""]
    k = sum(int(r["with_leader"]) for r in d)
    ct = [r for r in d if r["cites_tally"] == "1"]
    nc = [r for r in d if r["cites_tally"] != "1"]
    print(f"\npooled ({len(pool)} votes, no approval round, no switches): ballots {len(allb)}, "
          f"cite the tally {sum(r['cites_tally'] == '1' for r in allb)}")
    print(f"  with a strict earlier leader: {len(d)}; went to it: {k} ({k / len(d):.0%})")
    print(f"    citing the tally: {sum(int(r['with_leader']) for r in ct)}/{len(ct)}; "
          f"not citing: {sum(int(r['with_leader']) for r in nc)}/{len(nc)}")
    def matches(r):
        return r["choice"].lstrip("#") == votes[r["vote"]]["result"].lstrip("#")
    firsts = [vr[0] for vr in pool]
    later = [r for vr in pool for r in vr[1:]]
    print(f"  first ballot = announced result: {sum(map(matches, firsts))}/{len(firsts)}; "
          f"later ballots = result: {sum(map(matches, later))}/{len(later)}")
    contested = [vr for vr in pool if len({r["choice"] for r in vr}) > 1]
    print(f"  contested votes (>1 choice): {len(contested)} — {', '.join(vr[0]['vote'] for vr in contested)}")
    rng = np.random.default_rng(9)
    # primary order test: are minority (non-top) ballots placed earlier than chance within each vote?
    tested, obs_sum, pos, idx = [], 0, [], []
    for vr in contested:
        c = Counter(r["choice"] for r in vr).most_common()
        if len(c) > 1 and c[0][1] == c[1][1]:
            print(f"    {vr[0]['vote']}: top choice tied ({c[0][1]}-{c[1][1]}), left out of the order test")
            continue
        mino = np.array([r["choice"] != c[0][0] for r in vr])
        ranks = np.arange(1, len(vr) + 1)
        tested.append(vr[0]["vote"]); obs_sum += ranks[mino].sum()
        pos += list((ranks[mino] - 1) / (len(vr) - 1)); idx.append((len(vr), int(mino.sum())))
    null = np.array([sum(rng.permutation(n)[:m].sum() + m for n, m in idx) for _ in range(a.n)])
    print(f"  ORDER TEST (minority ballots earlier than chance?), {len(tested)} votes ({', '.join(tested)}), "
          f"{sum(m for _, m in idx)} minority ballots: rank sum {obs_sum}, shuffled mean {null.mean():.1f}, "
          f"p(<=obs) {(null <= obs_sum).mean():.3f}; mean normalised position {np.mean(pos):.2f} (0 = first, 1 = last, "
          f"chance 0.50)")
    # remark only: with first-ballot choices fixed, agreement with a strict earlier leader is set up to ties
    seqs = [[(r["agent"], r["choice"]) for r in vr] for vr in contested]
    cobs = sum(with_leader_count(s) for s in seqs)
    tj = []
    for _ in range(a.n):
        tot = 0
        for s in seqs:
            ch = [c for _, c in s]
            rng.shuffle(ch)
            tot += with_leader_count([(ag, c) for (ag, _), c in zip(s, ch)])
        tj.append(tot)
    tj = np.array(tj)
    print(f"  remark (tie-joining, not a herding test): {cobs} ballots agree with a strict earlier leader; shuffled "
          f"mean {tj.mean():.2f}, p(>=obs) {(tj >= cobs).mean():.3f}")

if __name__ == "__main__":
    main()
