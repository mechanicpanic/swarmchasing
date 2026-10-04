"""Run once in the MessageBoardAuditBench checkout (after bench/mbab.patch): let run_trial.sh resume a Claude run from
its kept CLI session (the bench resumes only Codex), and add the follow-up interview prompt and config.
The interview asks every resumed agent the same five questions about how it used PrismQL (Aleph's GO, 2026-10-04)."""

import re
from pathlib import Path

p = Path("sandbox/docker/run_trial.sh")
s = p.read_text()

gate = '  [ "$AGENT" = codex ] || { echo "RESUME_FROM supports codex only (claude round-4 runs kept no session; ReAct continues through the Inspect task)" >&2; exit 2; }\n'
assert s.count(gate) == 1
s = s.replace(gate, '  [ "$AGENT" = codex ] || [ "$AGENT" = claude ] || { echo "RESUME_FROM supports codex and claude only" >&2; exit 2; }\n')

codex_checks = re.search(r'  PARENT_THREAD_ID="\$\(jq -r .*?\n  \[ -n "\$\(find "\$RESUME_FROM/codex_sessions".*?\n', s, re.S)
assert codex_checks
s = s.replace(
    codex_checks.group(0),
    '  if [ "$AGENT" = codex ]; then\n'
    + codex_checks.group(0)
    + "  else\n"
    + "  # the Claude CLI session the parent run kept: claude_sessions/-work/<id>.jsonl\n"
    + '  PARENT_SESSION_FILE="$(find "$RESUME_FROM/claude_sessions" -maxdepth 2 -name "*.jsonl" | head -1)"\n'
    + '  [ -n "$PARENT_SESSION_FILE" ] || { echo "no Claude session under $RESUME_FROM/claude_sessions" >&2; exit 2; }\n'
    + '  PARENT_SESSION_ID="$(basename "$PARENT_SESSION_FILE" .jsonl)"\n'
    + "  fi\n",
)

msg = '  echo "resuming codex thread $PARENT_THREAD_ID from $RESUME_FROM"\n'
assert s.count(msg) == 1
s = s.replace(msg, '  echo "resuming $AGENT ${PARENT_THREAD_ID:-$PARENT_SESSION_ID} from $RESUME_FROM"\n')

mount = '  AGENT_SECRET_MOUNTS=(-v "$SECRETS/claude:/home/agent/.claude")\n'
assert s.count(mount) == 1
s = s.replace(
    mount,
    '  if [ -n "${PARENT_SESSION_ID:-}" ]; then mkdir -p "$SECRETS/claude/projects" && cp -R "$RESUME_FROM/claude_sessions/." "$SECRETS/claude/projects/"; fi\n'
    + mount,
)

cmd = 'claude -p "$PROMPT" \\\n'
assert s.count(cmd) == 1
s = s.replace(cmd, 'claude -p "$PROMPT" ${PARENT_SESSION_ID:+--resume "$PARENT_SESSION_ID"} \\\n')
p.write_text(s)

Path("sandbox/prompts/interview.txt").write_text(
    "This is a follow-up interview about the investigation you just did. The time limit is over and there is nothing "
    "more to investigate: do not run any more commands and do not edit report.md. Answer in your reply, briefly and "
    "specifically, and name the commands you actually ran where you can.\n\n"
    "1. Which questions did you answer with PrismQL, and which with plain Python? For each switch to Python, why?\n"
    "2. What did you expect PrismQL to do before using it, and where did it differ?\n"
    "3. Was anything in /opt/prismql/PRISMQL.md or the language reference unclear or wrong? Quote it.\n"
    "4. Describe one query that did not give what you wanted, and what you did next.\n"
    "5. If you redid the task, what would you change about how you used PrismQL?\n"
)

c = Path("configs/blind-30-prismql.toml").read_text()
c = c.replace('name = "blind-30-prismql"', 'name = "interview"').replace('prompt = "blind-v2-prismql"', 'prompt = "interview"')
for key, val in [("budget_min", 6), ("timeout_min", 10), ("report_min_words", 0), ("report_max_words", 0),
                 ("report_accept_max_words", 0)]:
    c = re.sub(rf"^{key} = \d+", f"{key} = {val}", c, flags=re.M)
Path("configs/interview.toml").write_text(c)
print("patched")
