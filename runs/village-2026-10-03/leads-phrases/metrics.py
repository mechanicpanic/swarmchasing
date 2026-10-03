# Stage 4: per-candidate first-use hazard ratio (contagion thread's definition) + spread metrics.
import polars as pl, numpy as np, json, gzip
G0 = "/Users/phosphorus/projects/prismql-data/ai-village/"
P = pl.read_parquet("pool_scan.parquet")
chat = pl.read_parquet("chat_index.parquet")  # i,id,time,kind,agent,room,lab
DS = pl.col("agent")=="DeepSeek-V3.2"
chat = chat.with_columns(pl.when(DS & (pl.col("time")<pl.datetime(2026,4,22))).then(pl.lit("DeepSeek-V3.2"))
    .when(DS & (pl.col("time")>=pl.datetime(2026,4,25))).then(pl.lit("DeepSeek-V3.2>V4Flash"))
    .when(DS).then(pl.lit("DeepSeek-V3.2 (swap gap)")).otherwise(pl.col("agent")).alias("ag2"))
hits = pl.read_parquet("chat_hits.parquet").join(chat, on="i")
mem = pl.read_parquet("mem_hits.parquet")
END = chat["time"].max()
ainfo = (chat.filter(pl.col("kind")=="agent").group_by("ag2").agg(pl.len().alias("n"), pl.col("lab").first().alias("alab"),
         pl.col("time").min().alias("arrive"), pl.col("time").max().alias("leave")))
leave_raw = dict(chat.filter(pl.col("kind")=="agent").group_by("agent").agg(pl.col("time").max()).iter_rows())
risk_agents = ainfo.filter((pl.col("n")>=100) & (pl.col("ag2")!="DeepSeek-V3.2 (swap gap)"))["ag2"].to_list()
A = chat.filter((pl.col("kind")=="agent") & pl.col("ag2").is_in(risk_agents)).select("i","time","room","ag2").sort("time")
goals = sorted([json.loads(l) for l in gzip.open(G0+"village_goals.jsonl.gz")], key=lambda r: r["start_time"])
gs = [(np.datetime64(g["start_time"]), np.datetime64(g["end_time"]) if g["end_time"] else np.datetime64(END), g["goal"]) for g in goals]
def goal_at(t):
    t = np.datetime64(t); cur = None
    for s,e,g in gs:
        if s <= t: cur = (s,e,g)
    return cur
H = np.timedelta64(1,"h")
rows, adopt_rows = [], []
for c in P.iter_rows(named=True):
    cid = c["cid"]; h = hits.filter(pl.col("cid")==cid).sort("time")
    ah = h.filter(pl.col("kind")=="agent")
    if ah.height == 0: continue
    hum_first = h.filter(pl.col("kind")=="user")["time"].min()
    gfirst = h["time"].min(); a_first = ah["time"][0]; origin = ah["ag2"][0]; olab = ah["lab"][0]
    fu = ah.group_by("ag2").agg(pl.col("time").min().alias("fu"), pl.len().alias("uses_a"), pl.col("lab").first().alias("lab")).sort("fu")
    # exposure: last hit (anyone) in same room strictly before each agent message
    hh = h.select(pl.col("time").alias("t_o"), "room", pl.col("ag2").alias("src"), pl.col("kind").alias("src_kind")).sort("t_o")
    m = A.filter(pl.col("time")>gfirst).join(fu.select("ag2","fu"), on="ag2", how="left")
    m = m.filter(pl.col("fu").is_null() | (pl.col("time")<=pl.col("fu")))
    m = m.join_asof(hh, left_on="time", right_on="t_o", by="room", strategy="backward", allow_exact_matches=False)
    m = m.with_columns((pl.col("t_o").is_not_null() & ((pl.col("time")-pl.col("t_o"))<=pl.duration(hours=1))).alias("exp"),
                       (pl.col("time")==pl.col("fu")).alias("ev")).filter(pl.col("ag2")!=origin)
    a = int((m["ev"]&m["exp"]).sum()); n1 = int(m["exp"].sum()); b = int((m["ev"]&~m["exp"]).sum()); n0 = m.height-n1
    hr_raw = (a/n1)/(b/n0) if (n1 and n0 and b) else None
    hr_cc = ((a+0.5)/(n1+0.5))/((b+0.5)/(n0+0.5)) if (n1+n0) else None
    # adopters (non-origin)
    ad = (m.filter("ev").select("ag2","time","exp","src","t_o").rename({"time":"fu"}))
    ad = ad.join(ainfo.select("ag2","arrive","alab"), on="ag2", how="left")
    ad = ad.join_asof(ah.select(pl.col("time").alias("t_ever"), pl.col("ag2").alias("ever_src")).sort("t_ever"), left_on="fu", right_on="t_ever",
                      strategy="backward", allow_exact_matches=False)
    ad = ad.join(mem.filter(pl.col("cid")==cid).select(pl.col("agent").alias("ag2"), "m_first"), on="ag2", how="left")
    ad = ad.with_columns(((pl.col("fu")-pl.col("t_ever")).dt.total_seconds()/3600).alias("h_since_other"),
                         (pl.col("m_first").is_not_null() & (pl.col("m_first")<pl.col("fu"))).alias("mem_before"),
                         ((pl.col("fu")-pl.col("arrive")).dt.total_seconds()/3600).alias("h_since_arrival"),
                         (pl.col("arrive")>gfirst).alias("newcomer"))
    ad = ad.with_columns(pl.when(pl.col("exp")).then(pl.lit("room_1h"))
                          .when(pl.col("h_since_other")<=24).then(pl.lit("heard_24h"))
                          .when(pl.col("mem_before")).then(pl.lit("own_memory"))
                          .otherwise(pl.lit("cold")).alias("channel"))
    for r in ad.iter_rows(named=True): adopt_rows.append(dict(cid=cid, key=c["key"], agent=r["ag2"], lab=r["alab"], first_use=r["fu"], channel=r["channel"],
        src=r["src"] if r["exp"] else None, nearest_earlier=r["ever_src"], h_since_other=r["h_since_other"], newcomer=r["newcomer"], h_since_arrival=r["h_since_arrival"]))
    ts = fu["fu"].to_list()
    t5 = (ts[4]-a_first).total_seconds()/3600 if len(ts)>=5 else None
    t4 = (ts[3]-a_first).total_seconds()/3600 if len(ts)>=4 else None
    labs = fu["lab"].unique().to_list()
    xl = fu.filter(pl.col("lab")!=olab)["fu"].min()
    g = goal_at(a_first); gstart, gend, gtext = g if g else (None,None,"")
    gend_dt = gend.astype("datetime64[us]").item() if g else None
    gstart_dt = gstart.astype("datetime64[us]").item() if g else None
    after_goal = ah.filter(pl.col("time")>gend_dt) if g else ah.head(0)
    gwords = set(w for w in "".join(ch if ch.isalnum() else " " for ch in gtext.lower()).split())
    kw = c["key"].split()
    origin_leave = leave_raw[origin.split(">")[0].replace(" (swap gap)","")]
    last = ah["time"].max()
    mm = mem.filter(pl.col("cid")==cid)
    rows.append(dict(cid=cid, key=c["key"], form=c["form"], src_stream=c["src"], first_time=a_first, origin=origin, origin_lab=olab,
        human_first=hum_first, human_born=(hum_first is not None and hum_first < a_first),
        uses_agent=ah.height, uses_human=h.height-ah.height, n_agents=fu.height, n_adopters=ad.height, n_labs=len(labs), labs=",".join(sorted(labs)),
        cross_lab_h=((xl-a_first).total_seconds()/3600 if xl is not None else None),
        t4_h=t4, t5_h=t5, last_use=last, lifespan_d=(last-a_first).total_seconds()/86400,
        n_rooms=h["room"].n_unique(),
        adopt_exp=a, exp_msgs=n1, adopt_unexp=b, unexp_msgs=n0, HR=hr_raw, HR_cc=hr_cc,
        frac_first_exposed=(a/(a+b) if a+b else None),
        ch_room_1h=int((ad["channel"]=="room_1h").sum()), ch_heard_24h=int((ad["channel"]=="heard_24h").sum()),
        ch_own_memory=int((ad["channel"]=="own_memory").sum()), ch_cold=int((ad["channel"]=="cold").sum()),
        newcomer_adopters=int(ad["newcomer"].sum()),
        newcomer_fast_2h=int((ad["newcomer"] & (ad["h_since_arrival"]<=2)).sum()),
        mem_agents=mm.height, mem_uses=int(mm["m_n"].sum()) if mm.height else 0,
        mem_first_adopters=int(ad["mem_before"].sum()),
        goal_at_birth=gtext, goal_start=gstart_dt, goal_end=gend_dt,
        h_after_goal_start=((a_first-gstart_dt).total_seconds()/3600 if g else None),
        in_goal_text=(all(w in gwords for w in kw) or (c["key"] in gtext.lower())),
        any_word_in_goal=any(w in gwords and len(w)>3 for w in kw),
        uses_after_goal_end=after_goal.height, agents_after_goal_end=after_goal["ag2"].n_unique(),
        days_used_after_goal_end=((last-gend_dt).total_seconds()/86400 if g and last>gend_dt else 0.0),
        origin_left=origin_leave, origin_gone=(END-origin_leave).total_seconds()/86400>30,
        uses_after_origin_left=ah.filter(pl.col("time")>origin_leave).height,
        died_with_origin=((END-origin_leave).total_seconds()/86400>30) and (last-origin_leave).total_seconds()/86400<14))
R = pl.DataFrame(rows, infer_schema_length=None)
R = R.with_columns((((pl.col("h_after_goal_start")<48) & (pl.col("t4_h")<24)) | pl.col("in_goal_text")).alias("broadcast"))
R.write_parquet("metrics_raw.parquet"); pl.DataFrame(adopt_rows, infer_schema_length=None).write_parquet("adoptions.parquet")
print(R.height)
