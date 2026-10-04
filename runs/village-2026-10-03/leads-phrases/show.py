# Print birth message + first adoptions for given keys (for reading).
import polars as pl, sys, re
C = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
R = pl.read_parquet("phrase_spread.parquet"); A = pl.read_parquet("adoptions.parquet")
idx = pl.read_parquet("chat_index.parquet"); hits = pl.read_parquet("chat_hits.parquet")
txt = pl.read_parquet(C+"chat_raw.parquet", columns=["id","text"])
N = int(sys.argv[1]) if sys.argv[1].isdigit() else 3
for k in [a for a in sys.argv[1:] if not a.isdigit()]:
    r = R.filter(pl.col("key")==k)
    if not r.height: print("??", k); continue
    r = r.row(0, named=True)
    print(f"\n=== {r['form']} | origin {r['origin']} {str(r['first_time'])[:16]} | agents {r['n_agents']} labs {r['n_labs']} uses {r['uses_agent']} HR_cc {r['HR_cc']:.0f} t5h {r['t5_h']} life {r['lifespan_d']:.0f}d last {str(r['last_use'])[:10]} | goal: {r['goal_at_birth'][:50]} | variants {r['variants']}")
    h = hits.filter(pl.col("cid")==r["cid"]).join(idx, on="i").sort("time").join(txt, on="id")
    # birth + first use per agent
    f = h.filter(pl.col("kind")=="agent").unique("agent", keep="first", maintain_order=True).head(N+1)
    pre = h.filter(pl.col("time")<r["first_time"])
    if pre.height: print("  [human earlier]", pre.height)
    ad = A.filter(pl.col("key")==k)
    for row in f.iter_rows(named=True):
        t = re.sub(r"\s+"," ", row["text"]); m = re.search(r"[^A-Za-z0-9]"+r"[^A-Za-z0-9']+".join(re.escape(w) for w in k.split()), t, re.I)
        s = max(0,(m.start() if m else 0)-120); 
        a = ad.filter(pl.col("agent")==row["agent"])
        ch = f"{a['channel'][0]} src={a['src'][0]} near={a['nearest_earlier'][0]}" if a.height else "ORIGIN"
        print(f"  {str(row['time'])[:16]} {row['agent']} [{row['room']}] ({ch}): …{t[s:s+300]}")
