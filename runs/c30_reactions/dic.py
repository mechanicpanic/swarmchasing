"""C30 norm/apology/repair dictionary (case-insensitive regex over a save's added text). v2: overwrite/accident
only in loss or prohibition forms (v1 hit 'overwrite this page with R5' and 'accidental endpoint test')."""
DIC = r"(?i)" + "|".join([
    r"accidentally (?:overwr|truncat|delet|remov|revert|replac|eras|wip|clobber)",
    r"overwritten|overwrote (?:my|our|the|your|it|this)|(?:was|were|got|been|being) overwr",
    r"apolog", r"\bsorry\b",
    r"\brestor(?:e|ed|ing)\b",
    r"append[ _-]?only|only append|append (?:below|at the end|don)",
    r"(?:don.?t|do not|please not|never|avoid|stop) (?:overwrit|delet|remov|replac|eras|wip|clobber)",
    r"\b(?:was|were|got|been) (?:lost|deleted|removed|wiped|erased|clobbered|truncated|reverted)",
    r"clobber", r"\bwiped\b", r"contention", r"edit conflict",
    r"use (?:this|the|our) (?:relay|page)",
    r"\bre-?post(?:ed|ing)?\b",
    r"keep (?:all|prior|previous|earlier) (?:messages|lines|posts|entries)",
])
