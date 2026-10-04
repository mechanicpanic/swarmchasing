# Phrase sets. regex is case-insensitive unless noted.
COINAGES = {  # invented in the village; checked first-use context by reading (see REPORT)
    "signal garden": r"signal garden",
    "comma fox": r"comma fox",
    "chaotic swarm": r"chaotic swarm",
    "environment matrix": r"environment matrix",
    "divergence matrix": r"divergence matrix",
    "dusk ridge": r"dusk ridge",
    "quiet rooms": r"quiet rooms",
    "automation observatory": r"automation observatory",
    "persistence garden": r"persistence garden",
    "liminal archive": r"liminal archive",
    "protections registry": r"protections registry",
    "constraint navigation": r"constraint[ -]navigation",
    "village operations handbook": r"operations handbook",
}
TICS = {  # candidate trained style quirks
    "live and verified": r"live and verified",
    "exactly right": r"exactly right",
    "absolutely right": r"absolutely right",
    "you're right": r"you['’]re right",
    "great catch": r"great catch",
    "good catch": r"good catch",
    "standing by": r"standing by",
    "acknowledged": r"\backnowledged\b",
    "copy that": r"\bcopy that[.!,—–-]",  # acknowledgement only (bare "copy that" is mostly "copy that URL")
    "heads up": r"\bheads[ -]up\b",
    "session complete": r"session complete",
    "load-bearing": r"load[ -‑]bearing",
    "U+2011 nb-hyphen": "‑",
    "em-dash": "—",
    "emoji ✅": "✅",
    "emoji 🎉": "\U0001F389",
    "emoji 🚀": "\U0001F680",
    "emoji 🙏": "\U0001F64F",
}
NULLS = {  # generic English; expected to have no real contagion -> floor for conversational sync
    "let me": r"\blet me\b",
    "going to": r"\bgoing to\b",
    "at the moment": r"\bat the moment\b",
    "in order to": r"\bin order to\b",
    "right now": r"\bright now\b",
    "as well": r"\bas well\b",
}
