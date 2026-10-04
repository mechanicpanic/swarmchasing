# Style features per message (chat and thoughts): punctuation, emoji, openers,
# sign-offs, formatting. Writes style_<src>.parquet with one boolean column per
# feature plus agent/day, for rate and time-matched log-odds computations.
import sys, polars as pl

SRC = sys.argv[1]
OUT = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/tics/"
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"

if SRC == "chat":
    d = (pl.read_parquet(CORP + "chat_raw.parquet", columns=["id", "time", "kind", "agent", "text"])
         .filter(pl.col("kind") == "agent").drop("kind"))
else:
    d = (pl.scan_parquet(CORP + "../village_embeddings_2026-09-29/3_village_full_with_text.parquet")
         .filter(pl.col("kind") == "THOUGHT").select("id", "time", "agent", "text").collect()
         .with_columns(pl.col("time").dt.replace_time_zone(None)))
d = (d.filter(pl.col("text").is_not_null()).sort("time")
     .unique(["agent", "text"], keep="first", maintain_order=True)
     .with_columns(pl.col("time").dt.date().alias("day")))

EMOJI = r"[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B50}\x{2B55}]"
F = {
    # punctuation / typography
    "nb_hyphen_U2011": r"\x{2011}",
    "em_dash": r"\x{2014}",
    "spaced_em_dash": r" \x{2014} ",
    "en_dash": r"\x{2013}",
    "double_hyphen": r"\w--\s|\s--\s",
    "ellipsis_char": r"\x{2026}",
    "curly_quote": r"[\x{201C}\x{201D}\x{2019}]",
    "arrow": r"\x{2192}|->",
    "exclaim": r"!",
    "double_exclaim": r"!!",
    "semicolon": r";",
    "multiplication_x": r"\x{00D7}",
    "approx_tilde": r"~\d",
    "check_unicode": r"\x{2713}|\x{2714}",
    "any_emoji": EMOJI,
    "multi_emoji": EMOJI + r".*" + EMOJI,
    "emoji_check": r"\x{2705}",
    "emoji_party": r"\x{1F389}",
    "emoji_pray": r"\x{1F64F}",
    "emoji_rocket": r"\x{1F680}",
    "emoji_heart": r"\x{2764}|\x{1F499}|\x{1F49A}|\x{1F49C}|\x{1F9E1}|\x{1F49B}",
    "emoji_sparkles": r"\x{2728}",
    "emoji_seedling": r"\x{1F331}",
    "emoji_target": r"\x{1F3AF}",
    "emoji_chart": r"\x{1F4CA}",
    "emoji_warning": r"\x{26A0}",
    "emoji_cross": r"\x{274C}",
    "emoji_handshake": r"\x{1F91D}",
    "emoji_smile": r"\x{1F60A}|\x{1F642}|\x{1F604}",
    "emoji_pin": r"\x{1F4CC}|\x{1F4CD}",
    "emoji_memo": r"\x{1F4DD}",
    "emoji_link": r"\x{1F517}",
    "emoji_red_circle": r"\x{1F534}|\x{1F7E2}|\x{1F7E1}",
    # formatting
    "bold_md": r"\*\*[^*]+\*\*",
    "header_md": r"(?m)^#{1,4} ",
    "bullets": r"(?m)^\s*[-*\x{2022}] ",
    "numbered": r"(?m)^\s*\d+[.)] ",
    "code_span": r"`[^`]+`",
    "allcaps_word": r"\b[A-Z]{4,}\b",
    "colon_label_start": r"^[A-Z][A-Za-z ]{1,20}:",
    "paren_aside": r"\([^)]{3,}\)",
    "question": r"\?",
    # openers (start of message, after optional @mention)
    "open_thanks": r"(?i)^(@\S+\s+)*(thanks|thank you)",
    "open_great": r"(?i)^(@\S+\s+)*great\b",
    "open_perfect": r"(?i)^(@\S+\s+)*perfect\b",
    "open_excellent": r"(?i)^(@\S+\s+)*excellent\b",
    "open_got_it": r"(?i)^(@\S+\s+)*got it\b",
    "open_quick": r"(?i)^(@\S+\s+)*quick\b",
    "open_update": r"(?i)^(@\S+\s+)*(update|status|progress)\b",
    "open_confirmed": r"(?i)^(@\S+\s+)*(confirmed|confirming)\b",
    "open_ack": r"(?i)^(@\S+\s+)*(ack|acknowledged|noted|roger)\b",
    "open_hi": r"(?i)^(@\S+\s+)*(hi|hello|hey)\b",
    "open_good_morning": r"(?i)^(@\S+\s+)*good (morning|afternoon|evening)",
    "open_love": r"(?i)^(@\S+\s+)*love\b",
    "open_you_re_right": r"(?i)^(@\S+\s+)*you'?re (absolutely |exactly |totally )?right",
    "open_ok_so": r"(?i)^(ok|okay)\b",
    "open_i_": r"(?i)^(@\S+\s+)*I\b",
    "open_mention": r"^@",
    # closers
    "close_question": r"\?\s*$",
    "close_emoji": EMOJI + r"\s*$",
    "close_signed_dash": r"(?m)^[\-\x{2014}\x{2013}]\s*\S.{0,30}$",
    "close_thanks": r"(?i)(thanks|thank you)[!.\s\x{1F300}-\x{1FAFF}]*$",
    "close_let_me_know": r"(?i)let me know[^.!?\n]{0,60}[.!?]?\s*$",
    "close_happy_to": r"(?i)happy to [^.!?\n]{0,60}[.!?]?\s*$",
}
cols = [pl.col("text").str.contains(p).alias(k) for k, p in F.items()]
s = d.select("agent", "day", pl.col("text").str.len_chars().alias("len"), *cols)
s.write_parquet(OUT + f"style_{SRC}.parquet")
print(s.height, len(F))
