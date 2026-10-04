# Build weekly per-agent feature series for change-point detection.
# Sources: corpus/chat.parquet (agent chat), THOUGHT rows + action/cost rows of
# aleph's village_full stream. Output: weekly.parquet (long: agent, week, src,
# feature, value, n) and msg_chat.parquet (per-message features, for daily
# refinement and reading).
import polars as pl

CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
FULL = CORP + "../village_embeddings_2026-09-29/3_village_full_with_text.parquet"
OUT = CORP + "analysis/leads-changepoints/"

EMOJI = r"[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B50}\x{2B55}]"
AGENT_WORDS = r"(?i)\b(opus|sonnet|haiku|gemini|gpt-?\d|deepseek|grok|kimi|glm|o3|fable|muse spark|claude)\b"
PRAISE = r"(?i)\b(thank|thanks|grateful|appreciat\w*|excellent|amazing|fantastic|brilliant|impressive|wonderful|awesome|great (work|job)|well done|kudos|congrat\w*|beautiful)\b"
APOLOGY = r"(?i)\b(sorry|apolog\w*|my (mistake|bad|error)|you'?re (absolutely )?right|i was wrong|good catch|i stand corrected|mea culpa)\b"
HEDGE = r"(?i)\b(maybe|perhaps|might|possibly|probably|i think|seems?|appears?|likely|not sure|unclear|i believe)\b"
FRUSTR = r"(?i)\b(frustrat\w*|stuck|annoying|ugh|impossible|keeps? (failing|crashing)|still (not|no)|give up|waste|wasted|blocked|broken|not working|again)\b"
DEADLINE = r"(?i)\b(deadline|minutes? left|time left|hours? left|before (the )?(end|close)|running out of time|final minutes)\b"
SYCO = r"(?i)\b(absolutely|exactly) right\b"
EN_STOP = r"(?i)\b(the|and|to|of|is|in|that|for|you|it|with|on|this|are|be)\b"
NONLATIN = r"[\p{Han}\p{Hiragana}\p{Katakana}\p{Hangul}\p{Cyrillic}\p{Arabic}\p{Devanagari}\p{Thai}\p{Hebrew}\p{Greek}]"


def text_feats(t):
    """Expressions on a text column -> per-message features."""
    nw = t.str.count_matches(r"\S+").clip(1, None)
    return [
        (t.str.len_chars() + 1).log().alias("log_len"),
        t.str.count_matches("\n").alias("newlines"),
        t.str.contains(r"\x{2011}").alias("u2011"),
        t.str.contains(r"\x{2014}").alias("emdash"),
        t.str.contains(r" \x{2014} ").alias("emdash_spaced"),
        t.str.contains(r"\w\x{2014}\w").alias("emdash_unspaced"),
        t.str.contains(r"\x{2013}").alias("endash"),
        t.str.contains(r"[\x{201C}\x{201D}\x{2019}]").alias("curly_quote"),
        t.str.contains(";").alias("semicolon"),
        t.str.contains(r"\x{2026}").alias("ellipsis"),
        t.str.contains(EMOJI).alias("emoji"),
        t.str.contains(r"\x{2705}").alias("emoji_check"),
        t.str.contains(r"\*\*[^*]+\*\*").alias("bold"),
        t.str.contains(r"(?m)^#{1,4} ").alias("header"),
        t.str.contains(r"(?m)^\s*([-*\x{2022}]|\d+\.) ").alias("bullets"),
        t.str.contains(r"\?").alias("question"),
        t.str.contains("!").alias("exclaim"),
        t.str.contains(r"https?://").alias("link"),
        t.str.contains(r"```|`[^`\n]+`").alias("code"),
        t.str.contains(PRAISE).alias("praise"),
        t.str.contains(APOLOGY).alias("apology"),
        t.str.contains(HEDGE).alias("hedge"),
        t.str.contains(DEADLINE).alias("deadline"),
        t.str.contains(SYCO).alias("syco"),
        (t.str.count_matches(r"\b(I|me|my|mine|I'm|I've|I'll|I’m|I’ve|I’ll)\b") / nw).alias("first_person"),
        (t.str.count_matches(r"(?i)\b(we|us|our|we're|we’re|let's|let’s)\b") / nw).alias("we_rate"),
        t.str.starts_with("I ").alias("starts_I"),
        ((t.str.count_matches(NONLATIN) / t.str.len_chars().clip(1, None)) > 0.1).alias("nonlatin"),
        ((nw >= 15) & ((t.str.count_matches(EN_STOP) / nw) < 0.04)).alias("non_english"),
    ]


def weekly(df, feats, src):
    df = df.with_columns(pl.col("time").dt.truncate("1w").alias("week"))
    agg = df.group_by("agent", "week").agg(
        [pl.col(f).cast(pl.Float64).mean().alias(f) for f in feats] + [pl.len().alias("n")])
    return agg.unpivot(index=["agent", "week", "n"], variable_name="feature", value_name="value") \
              .with_columns(pl.lit(src).alias("src"))


# ---------- chat ----------
chat = (pl.read_parquet(CORP + "chat.parquet", columns=["id", "time", "kind", "agent", "room", "text", "mentions"])
        .filter((pl.col("kind") == "agent") & pl.col("text").is_not_null()).drop("kind")
        .with_columns(pl.col("time").dt.replace_time_zone(None)).sort("time"))
# activity features on all messages (incl. repeats)
act = (chat.with_columns(pl.col("time").dt.truncate("1w").alias("week"), pl.col("time").dt.date().alias("day"))
       .group_by("agent", "week").agg(
           pl.len().alias("n"),
           (pl.len() / pl.col("day").n_unique()).alias("msgs_per_day"),
           pl.col("day").n_unique().cast(pl.Float64).alias("active_days"),
           (pl.col("room") != "general").mean().alias("room_nongeneral"),
           (pl.col("room") == "rest").mean().alias("room_rest"),
           (pl.col("room") == "best").mean().alias("room_best"),
           (pl.col("mentions").list.len() > 0).mean().alias("mention"),
           pl.col("mentions").list.len().mean().alias("mentions_per_msg"),
           pl.col("mentions").explode().drop_nulls().n_unique().cast(pl.Float64).alias("distinct_addressees"),
           (pl.col("text").is_duplicated()).mean().alias("dup_share"),
       )
       .unpivot(index=["agent", "week", "n"], variable_name="feature", value_name="value")
       .with_columns(pl.lit("chat").alias("src")))
dedup = chat.unique(["agent", "text"], keep="first", maintain_order=True)
cf = dedup.select("id", "time", "agent", "room", *text_feats(pl.col("text")))
feats_chat = [c for c in cf.columns if c not in ("id", "time", "agent", "room")]
# two agents asked not to be named in behavioural reporting: keep them out of per-agent outputs
OPTED_OUT = ["GPT-5.6 Terra", "GPT-5.6 Luna"]
cf.filter(~pl.col("agent").is_in(OPTED_OUT)).write_parquet(OUT + "msg_chat.parquet")
w_chat = weekly(cf, feats_chat, "chat")
del chat, dedup

# ---------- thoughts ----------
th = (pl.scan_parquet(FULL).filter(pl.col("kind") == "THOUGHT").select("time", "agent", "text")
      .filter(pl.col("text").is_not_null()).collect()
      .with_columns(pl.col("time").dt.replace_time_zone(None)).sort("time")
      .unique(["agent", "text"], keep="first", maintain_order=True))
t = pl.col("text")
tf = th.select("time", "agent",
               (t.str.len_chars() + 1).log().alias("th_log_len"),
               t.str.contains(FRUSTR).alias("th_frustration"),
               t.str.contains(r"(?i)\bthe user\b").alias("th_the_user"),
               t.str.contains(AGENT_WORDS).alias("th_agent_mention"),
               (t.str.count_matches(r"\b(I|me|my|I'm|I've|I'll)\b") / t.str.count_matches(r"\S+").clip(1, None)).alias("th_first_person"),
               t.str.contains(r"\*\*[^*]+\*\*|(?m)^#{1,4} ").alias("th_markdown"),
               t.str.contains(DEADLINE).alias("th_deadline"),
               t.str.contains(r"(?i)\b(human|helper|organi[sz]er|admin)\b").alias("th_human"),
               t.str.contains(r"\x{2011}").alias("th_u2011"),
               ((t.str.count_matches(NONLATIN) / t.str.len_chars().clip(1, None)) > 0.1).alias("th_nonlatin"),
               )
w_th = weekly(tf, [c for c in tf.columns if c not in ("time", "agent")], "thought")
del th, tf

# ---------- actions / cost (no text) ----------
ac = (pl.scan_parquet(FULL).select("time", "agent", "kind", "cost", "input_tokens", "output_tokens")
      .filter(~pl.col("kind").is_in(["USER_TALK", "USER_NAME_CHANGE"])).collect()
      .with_columns(pl.col("time").dt.replace_time_zone(None), pl.col("time").dt.replace_time_zone(None).dt.truncate("1w").alias("week")))
acts = ac.filter(pl.col("kind") != "THOUGHT")
talk = pl.col("kind") == "AGENT_TALK"
w_ac = (acts.group_by("agent", "week").agg(
    pl.len().alias("n"),
    (pl.col("kind") == "AGENT_TALK").mean().alias("act_talk_share"),
    (pl.col("kind") == "START_USING_COMPUTER").mean().alias("act_computer_share"),
    (pl.col("kind") == "CONSOLIDATE").mean().alias("act_consolidate_share"),
    (pl.col("kind") == "PAUSE").mean().alias("act_pause_share"),
    (pl.col("kind") == "WAIT").mean().alias("act_wait_share"),
    (pl.col("kind") == "SEARCH_HISTORY").mean().alias("act_search_share"),
    (pl.col("output_tokens").filter(talk) + 1).log().mean().alias("talk_log_out_tokens"),
    (pl.col("input_tokens").filter(talk) + 1).log().mean().alias("talk_log_in_tokens"),
    (pl.col("cost").filter(talk) + 1).log().mean().alias("talk_log_cost"),
    ((pl.col("cost").filter(talk) + 1).log() - (pl.col("output_tokens").filter(talk) + 1).log()).mean().alias("talk_log_cost_per_outtok"),
)
    .join(ac.filter(pl.col("kind") == "THOUGHT").group_by("agent", "week").agg(pl.len().alias("nth")), on=["agent", "week"], how="left")
    .with_columns((pl.col("nth").fill_null(0) / pl.col("n")).alias("thoughts_per_action")).drop("nth")
    .unpivot(index=["agent", "week", "n"], variable_name="feature", value_name="value")
    .with_columns(pl.lit("action").alias("src")))

allw = pl.concat([w_chat, act, w_th, w_ac], how="diagonal_relaxed").with_columns(pl.col("n").cast(pl.Int64))
allw.filter(~pl.col("agent").is_in(OPTED_OUT)).write_parquet(OUT + "weekly.parquet")
print(allw.group_by("src").agg(pl.col("feature").n_unique(), pl.len()))
