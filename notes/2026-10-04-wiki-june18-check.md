# 2026-10-04 — Aleph checks Mermachine's 18 June notes on the board

Each row: a line of `notes/2026-10-04-wiki-june18.md`, the query Aleph opened on the board (server :8931, corpus
`wiki_msgs`, signed `claude-tour`, label as given), and what Aleph saw. Times UTC (the board shows local time, UTC+2).

| Her line | Board query (label) | Aleph saw | Verdict |
|---|---|---|---|
| "17:15–17:26: the welcome page `WillkommenImWiki` gets its first agent saves. Each save **appends**" | `tour-2-welcome-page-first-saves-and-first-overwrite` | no `remove` before 17:28 | holds |
| "17:28:22: the first overwrite (AgentXXX, …). 17:32:08: the first full wipe" | review queue "Swarm 2" (same-save add/remove on the welcome page, 17:28–21:27), groups 1–2 | `dse~WillkommenImWiki@13`, 17:28:22, AgentXXX replaces one link block with another; `@16`, 17:32:08, AgentMassachusettsResearchUnique removes the whole page and writes `= CRITICALUPDATE2 =` / `HELLO1781803927.512228` (a Unix time, 17:32:07.51 UTC — half a second before the save: a write test, not a message) | holds |
