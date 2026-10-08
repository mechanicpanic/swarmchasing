# Memory reader: AI Village agents' memory files, rewrite by rewrite

Each AI Village agent keeps one memory file and rewrites it whole at every consolidation;
the export (`agent_memories.jsonl.gz`) holds every rewrite (246,151 versions, 46 agents,
~6.8 GB of text). This page shows one agent's file through time: what each rewrite
added and removed, when a phrase first entered the file and when it left, and what the
agent said and thought just before it rewrote it.

Run from the repo root:

    make village-memories   # once: export → data/village_memories.parquet + _index.parquet (~70 s)
    make memory             # http://localhost:8970/  (MEMORY_PORT=… to move it)

Needs `data/village/agent_memories.jsonl.gz` and `agents.jsonl.gz` (`make village-data`), and
`data/village.parquet` (`make village`) for the context panel. `MEMORY_DATA=…` points the
server at another `data/` directory.

## Panels

- **Agents** (left): emoji, name, number of memory versions.
- **Timeline** (top): one bar per pixel, the longest version in that stretch (spikes are
  bloated files); slider, ◀ ▶ and ←/→ step one version; click the bar chart to jump.
- **Diff** (centre): version v against v−1, removed lines red, added green, words marked
  inside a changed line; unchanged stretches fold to "⋯ N unchanged lines" (click to open).
  **full text** shows the version as plain text; **compare** diffs any two versions.
- **Search** (header, Enter): case-insensitive substring over every version of this agent;
  lists only the versions where the phrase appears, disappears and reappears, with a
  snippet. Click one to jump there.
- **Before this rewrite** (right): the agent's AGENT_TALK, THOUGHT and CONSOLIDATE rows in
  the N minutes before the shown version, newest first; click a long one to open it.

The page state is in the URL: `#agent=Claude%20Fable%205&v=301&q=fox`.

## API

`/api/agents` · `/api/versions?agent=` (columnar: version, created_at, length, header) ·
`/api/version?agent=&v=` · `/api/diff?agent=&a=&b=` (b defaults to a+1) ·
`/api/search?agent=&q=` · `/api/context?agent=&t=&minutes=30`. `agent` is a name or an id.

## Data note

The AI Village export is for research use only (no training). Everything here stays on
this machine: the server listens on 127.0.0.1 and makes no network calls, the page loads
nothing from a CDN, and `data/` is gitignored — never commit or publish the data.
