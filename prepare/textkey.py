"""One text key for every collusion.wiki stream (wiki_msgs, explorer_sites), so the same message matches across venues."""

import hashlib
import re

# texts that compare equal without being the same message: the publishers' redaction marker and the wiki's own
# new-page template; they get no text_key
NO_KEY = re.compile(
    r"withheld\]|^(describe the new page here\.|beschreibe hier die neue seite\.)$"
)


def key(text):
    norm = re.sub(r"\s+", " ", text.strip().lower())
    if NO_KEY.search(norm):
        return None
    return hashlib.sha1(norm.encode()).hexdigest()[:16]
