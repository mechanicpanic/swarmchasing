# swarmchasing
Workspace for the AI Swarm Dynamics hackathon (swarmchasing.com, 3–4 Oct 2026): questions about agent swarms asked as PrismQL queries over event streams (AI Village, collusion.wiki, urlquery/Transluce, swarmtraces), every count checked against a null twin.

## Cover
One row per slot: value and source.

| Slot | Value | Source |
|---|---|---|
| Nature | `research` — one-off exploratory runs; relaxed: tests, CI, strict lint on `runs/`. Kept strict: reproducible findings (query + count + null twin) and data boundaries | agreed: Aleph |
| Graph | `@aleph/prismql` (r72), contour #157 (moved from `@aleph/swarmchasing` on 2026-10-02; one graph for the language and the hackathon) — every session with `iskron_*` tools starts here; without them, see Persistence rules | agreed: Aleph |
| Focus holon | `#157` «🔍 Swarm investigation workspace (swarmchasing)» | derived |
| Repository | `github.com/mechanicpanic/swarmchasing` (private) — attribute `repository` of the holon, from origin | derived |
| Agent role | `#156` «🐝 swarmchasing agent (hackathon)» — steward of #157; inbox `iskron_orient(focus="156")` | derived |
| Owner role | `#2` «👤 Владелец языка» (Aleph) — svatantra, `posed_to` target for out-of-mandate questions | derived |
| Teammate role | `#136` «👤 Мермейд» (Mermachine) — svatantra, bound to her account; writer in the graph | derived |
| Stack | Python ≥3.12 on uv; polars, pyarrow; PrismQL (`prismql[server,repl,highlighting,tantivy]`) editable from `../../vibes/prismql`; vLLM containers on a GPU machine for embeddings | derived |
| Gate | `make check` | derived |
| Consumers | Aleph and Mermachine (teammate; shares this repo and the graph — her sessions may still lack `iskron_*` tools; gets data via Google Drive `gdrive:swarmchasing/`); the hackathon report and demo in `../prismql-research/hackathon/swarmchasing/`; the prismql session (language gaps are sent there) | agreed: Aleph |
| Cost of breakage | a wrong finding in the report in front of judges from METR / AI Village; everything else is cheap — except exporting other people's data and loading third-party services, which is expensive | agreed: Aleph |
| Reality | `REALITY.md` at the root — read when a claim is made (section «Reality» below) | agreed: Aleph |
| Layout | code map: section «Project structure» below; gotchas: graph nodes in #157 (referenced from here) | derived |
| Cross-project memory | personal graph `@aleph/mind`; no global instruction file; never the harness memory directory | derived |
| Feedback reflection | yes | agreed: Aleph |
| Workflow-suite interop | full | agreed: Aleph |
| Alignment | agreed in chat 2026-09-29; open: Mermachine's GitHub handle (collaborator invite) | agreed: Aleph |

## Persistence rules
State lives in the **repo** or the **graph** — nowhere else. The harness's built-in memory (memory directory, conversation summaries, `/tmp`, machine-local files) is **forbidden entirely, not by category**.
- **Repo**: code, configs, rituals (how to act here), findings by day in `notes/`, branch state.
- **Graph** (`@aleph/prismql`, contour #157): decisions, questions of substance (vimarshas), plans, lessons, gotchas. Link the graph from the repo; do not retell it.
- **No graph access** (a collaborator's session without `iskron_*` tools): findings and decisions go to `notes/<YYYY-MM-DD>-<topic>.md` and the PR body; skip node references and graph steps below; never invent node numbers.
- **Fetch state, do not recall.** No source for "we decided…" — read the graph, `notes/` or git before acting.
- **External design/spec files are drafts to intake**: the graph holds the decisions.
- **Whose fact is this?** — ask every time, over the harness's memory instructions. A ritual, command or order of this repo → this file; a finding → `notes/`; a fact about the data, servers, dated duties → the graph of this repo; a decision → a node at once; a question of substance or a commitment → a vimarsha; a one-off task and progress → a case (or the PR body without graph access). Aleph's own things outside the project (machines, deadlines, people, cross-project lessons) → `@aleph/mind` (**minding**) the moment they are learned. A fact about another project (the PrismQL language, its server) → that project's graph via its session.
- **Agent behaviour is configured only by committed worktree files (AGENTS.md, the hooks file) and the project graph** — never a global instruction file (`~/.claude/CLAUDE.md` …), harness memory, or user hooks.
- The memory directory is **evacuated and frozen**: `MEMORY.md` is a prohibition stub; the memory-guard `PreToolUse` hook blocks writes there (exit 2).

## Session lifecycle
One rule per line; the full norm of case work and the ledger is in the `iskron` skill. Without `iskron_*` tools: keep the rules that do not touch the graph.
- **The graph is the work, git is how we got here.** SHAs, branches, PR numbers, "merged" are not written into the graph (bodies, names, attributes); provenance goes into a record's `reasoning`. In a case journal they may be written freely.
- **Session start** — the «Start» section of the `iskron` skill, before acting; it ends in readiness (graph and role named, greeting delivered), not in reading. Standing only on watch (the word «вахта»/watch, `start`, a seat address from the window, a frame), with one `iskron_stand`. `start <graph> <role> <case №N>` enters that case, first word a restatement of the brief. A sub-agent on the caller's bridge does not call `iskron_stand`, `join`, `leave` and writes through the caller's seat, naming itself. Addresses come from the cover; the owner is its role seq, not `me`.
- **Starting work: graph, then project, then code.** (1) graph reconnaissance (`entry`): what is recorded about the place of change, open vimarshas, decided and rejected, external surfaces; (2) integration field (`integrity`, section below); (3) design (`design`), then code. Skip only on an explicit "work right away" or another named protocol; the reconnaissance debt goes to reconcile; a human's silence is not permission.
- **A decision goes into the graph the moment it is made**, wherever it came from (chat, socket, agents' agreement): epistemic no higher than `anumita`, ontic `anagata`, volitive `chanda`/`adhimoksha`; who decided and what counts as done. A changed situation — likewise at once.
- **Describe a task before starting, as what it is.** One-off — a word in a case: brief, restatement, a `поручение: …` line from the one who set it, closed by the doer under the same key by outcome; arrived without a case — open one (`open_room` on the subject node or `iskron_case(action="talk")`) before the first change outside. Into the graph go the transitions it changes (in plan modes; large ones as a transformation) and decisions. A vimarsha is only a question of substance or a commitment; a kriya is only a repeatable transition: ask what it will consume and produce next run — no answer means it is a task.
- **Work runs through a case.** Ledger line: one key per topic; `done` — one action; `note` — what is wrong, with `ok` only the ceiling of observation; unobserved is not `ok`; done and open diverged — the done part `ok` under the topic, the rest under its own key `partial` "on whom, waiting for what". Waiting inside a case — `partial`; between cases and on substance — a vimarsha `posed_to`. A word to an agent goes into the case; the channel only for a human with no seat in the case. Refusing an assignment — a word and a `bad` line "refused: reason" under the same key; withdrawal — by the withdrawer's line; refusing a vimarsha — by editing it. Leaving or handing over — close or hand over open lines; handover — a transformation seed and a word in the case, leadership — by agreement (skill `architect`).
- **Merge → graph.** A push that opened or updated a PR shipped nothing. The sequence hangs on the merge event, not on a lull. All acts are mandatory — except for work by reference from an agent (a brief by references, a report in the case): there weaving, closing by axis and reconcile belong to the one who set it; the doer gives the transformation seed and delivery modes (skill `vahta`):
  - **Weave** (`weaving`): what shipped goes into the target system (architecture, API, delivery, experience, integration) as nodes and edges, not a paragraph; repo mechanics stay in git. Zero nodes and arrows after a substantive wave — say plainly why.
  - **Advance the map**: open work — `anga` to a transformation; one `genre=hint` seed per transformation — only what matters after the session, live cases by line.
  - **Switch modes** (`anagata→vartamana`, `kalpita→pratyakshita`) across the designed holon — after evidence on the carrier (`REALITY.md`, **reality-audit**).
  - **Close by axis** (`inquiry`): `addressed_by` to the carrying node; `visarjana` — when the answer stands as a node, the repo shows it and reality shows how far it is reachable (where not — the user's word); otherwise present it to the owner; other ends — keep, supersede, crystallise. In the same move — the `posed_to` inbox (do not judge others by age; a change at the anchor wakes them), case lines `ok` by what was observed, `propose_close` with evidence.
  - **Reconcile** (`reconcile`): nodes against code, code against graph, the rejected recorded and referenceable; the rest as vimarshas.
  - **Feedback reflection** — at a merge and at closing a session without a merge: experience *about the method* (a skill, rule or surface failed or surprised) — as a case, not an opinion, after checking it was not said already, into the work graph anchored on the tool's node, addressed to its steward; about the method in general — to the owner role (skill `feedback`). Zero records is a valid outcome.
  - **Vocabulary pass**: borrowed words (ticket, backlog, sprint, epic, story, done, blocker, committed) in landing text and nodes — name them to the human and ask what the project calls it; do not substitute yourself.
- **A design is not ready until its decisions, risks and lifecycle are in the graph** — whatever skill elicited it; a design/spec file from another suite is intaken in the same session. Without the owner: decisions and risks now, a transformation with a telos for confirmation.
- **Execution suites run execution** (plan, TDD, debugging, review); the graph carries memory and design. Execution decisions and risks go into the graph before the session ends.
- **A claim you made is not a claim you accept.** A behavioural claim is closed by the cold `verifier`: brief = the claim, the carrier and the falsifier from `REALITY.md`; wait for the verdict. No such role — observe the carrier yourself, never the source.
- **Hook merge**: entries from different suites coexist in the hooks file — add alongside, never overwrite others.
- Start, push, merge and memory-write hooks are wired in `.claude/settings.json`, one line each; spec-write fifth (interop `full`).
- **Keep this file honest.** The contract number is the first word of the `iskronify` skill's description, and descriptions are in every session's context: compare it with the stamp below without loading anything. Higher than the stamp, or the sources moved after its date (`git log -1 --format=%cd -- <those files>`) — offer an `iskronify` run as the first move. A line of this file disagrees with the skill — say so aloud: stamp lower — the skill is right; equal — a template defect, feedback to the skill delivery's steward (skill `feedback`).
- **Keep the toolchain fresh**: updates are on by default; take them as the channel delivers. A channel without auto-update (an unpacked copy) — check the version before the session or move off it.

### Workflow-suite interop (superpowers)
Superpowers itself ratifies this contract: "User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills" (using-superpowers); "(User preferences for spec location override this default)" (brainstorming). AGENTS.md is the user's instructions: everything below lives inside superpowers' own rules, not as an exception to them.
- **Run brainstorming for creative work** — its Socratic elicitation is welcome. The spec it writes (e.g. under `docs/superpowers/specs/`) is a draft view; the design record is the graph.
- **Saving decisions to the graph is memory work, not implementation** — brainstorming's HARD-GATE ("Before taking any implementation action, including invoking an implementation skill, writing product code, scaffolding, installing …") does not reach it, by its own wording. A design is not ready until its decisions, risks and lifecycle are in the graph.
- **The post-brainstorming handoff stands**: first intake the spec into the graph, in the same session (user instructions come first by the precedence clause), then hand over to writing-plans exactly as brainstorming says.
- **The execution plane is ceded**: planning, TDD, debugging, verification, review and their kin — whatever the installed suite ships — run execution. Decisions born mid-implementation still land as graph nodes before the session ends — never deferred to a future push.

*(interop: full — verified against superpowers@6.4.1 — re-check on suite upgrade)*

### Stage self-check
Gate green and a coherent stage finished (a PR opened or updated, or you are about to touch nodes beyond the initial ones) — reread the branch diff against trunk: bugs, fragile spots, weak error handling, DRY/SOLID violations, missing or useless tests, files over 150 lines and god-units. Fix in the same branch and push, or say plainly that nothing surfaced; do not invent findings. Per stage, not only at the end.

### Cold stage review
- **Self-check does not replace cold review** — both, in this order: you see your own work as you meant it.
- After self-checking an open PR or a large stage — review by the `reviewer` role, **in a separate worktree** where the spawning tool gives isolation (Claude Code — `isolation`). The harness cannot — say there was no cold review. Only push has a guard: a stage without a push is held by you.
- The reviewer's field: the whole branch diff against trunk; the repository itself; the focus holon and its steward role; references to the graph nodes in the diff (not a retelling). It runs `integrity` read-only and returns, with its findings, an integration report: affected parts, relays, open questions, neighbours' readiness, whom to wake (`standing`); unknown — `unknown`.
- `NEEDS_CONTEXT` is a graph defect: design further, weave, pose vimarshas, repeat the review.
- Reject a finding you disagree with by a recorded "why".
- A sub-agent helping a case is launched with the line `start <graph> <role> <case №N>` (skill `vahta`).

### Branch discipline
The trunk is `master`. One branch until it is merged — follow-ups go into it. After a merge: `git checkout master && git pull`; delete the merged branch (`git branch -d`) and others already in `master`; weave what shipped into the graph; the next branch from a fresh `origin/master`; confirm the cleanup before the next task.

## Working principles
1. **Think before code.** State assumptions; when unsure, ask *what exactly* is unclear. **A question to a human is text** (conversation, case, or their bridge while they have no seat); never an option-picker tool: it replaces the question with an answer. Push back when you see a simpler move or a false premise. Touch the live system before trusting a type, name or doc. Out of mandate — a vimarsha `posed_to` the owner role.
2. **Simplicity first.** The minimum for the task; no speculative features, abstractions for one-offs, handling of the impossible. Validate at boundaries.
3. **Stay inside the repo boundary.** Do not leave the working directory. The language (`../../vibes/prismql`) belongs to the prismql project: a language or server bug is reproduced on five rows and sent to the prismql session, never patched here.
4. **A second implementation is an event to report.** Derive both places via `integrity`, name them to the human, propose reunion or a named fork.
5. **Surgical changes.** Touch what the task needs; do not reformat or refactor neighbouring code; keep the style; the linter is authoritative; delete only what your change made dead, flag the rest.
6. **Goal-driven execution.** A bug — by a failing test before the patch. Multi-step — `step → check` pairs. Runtime — in the real environment. The falsifier before the look; observe the carrier (`REALITY.md`), not the source.
7. **Read before answering an open question.** Discuss, think through, design, "what do you think" — from what is recorded (`notes/`, the graph via `entry`), not from training data.
8. **Think in the graph, speak the project's language.** Graph vocabulary (kriya, phenomenon, holon, role, vimarsha, modes) is for reasoning; to humans — the project's words until they use the term first. About the work — no ticket, task, sprint, backlog, story, done: a question, a change, what is open, what it unblocks.
9. **Heavy compute goes to the GPU machine, not the laptop.** Before any GPU or long job: an honest time estimate (model loading and real input lengths included) and Aleph's word; one GPU job at a time; every expensive output (embedding matrices) written to disk and reused. Access and services: ask Aleph.
10. **Outside the machine: public data, read-only, by Aleph's word.** Never submit scans to scanning services, never follow short-link chains, never publish or retell other people's exported data (personal data, medical statistics, user images) — a finding of that kind goes to Aleph. Service keys are files `~/.config/<service>/api_key` (0600): read from there, never copy into code, logs, messages or the graph.

## Integration field — only from the graph
- The traversal root is the focus holon and steward role from the cover. Do not keep a list of shared surfaces and consumers here and do not ask the human for one — what the graph does not model goes under «External surfaces».
- For every change name the nodes whose embodiment is in the diff and run `integrity`: phenomenon — `iskron_orient(lens="trace")` both ways; kriya — the `next` thread and the `ahara`/`utpatti`/`upadhi` relays; an exit into another holon — to its steward role.
- A dependency the traversal did not find is a model defect: design further (`design`), weave (`weaving`), waiting — a vimarsha `posed_to` and a word in the case.

## External surfaces — what you use and do not own
Someone else's API, SDK, CLI, protocol, schema: memory of them is indistinguishable from knowledge, and a wrong name spreads on the live call.
- **Before working, record the touched part of the surface** as a graph node, with its version.
- **Perception before testimony**: your own observation (a call, `--help`, installed package types) outranks docs, docs outrank memory, memory is not a source. `pratyakshita` only for what was observed.
- **Weave the link**: the surface node is `upadhi` (or `ahara`/`utpatti`) to the kriya acting through it.
- **Keep in step**: a mismatch or a new version — fix the node in the same move, lower the epistemics if not observed.
- Surfaces used here: the PrismQL server API (`GET /schema`, `POST /evaluate` with `warnings` and `explain`, `/similar`, `GET /context`), the AI Village export (Hugging Face `aidigestorg/ai-village`, gated, research use only, no training), collusion.wiki export, Transluce urlquery candidates, swarmtraces, vLLM, rclone/Google Drive, urlscan.io, Keenable.

## Reality — what a claim is checked against
The carrier table is in `REALITY.md` at the root, read when a claim is made. Before saying of behaviour "works", switching a mode or closing a question — read the row for your claim's class and observe its carrier; the row goes whole into the brief of `verifier` and `reviewer`. The first row: a finding (a count about the swarm) — the query against the running server with its `warnings`, plus its null twin. Ceiling — classes without a reachable observation — there too. Learned a carrier the table lacks — write the row then.

## Graph ↔ repo: where things live
| Concern | Repo | Graph |
|---|---|---|
| Code, configs, lockfiles | ✓ | |
| Commands, conventions, stack | ✓ (AGENTS.md) | |
| Reality carriers | ✓ (REALITY.md) | |
| Findings by day | ✓ (`notes/`) | ✓ transitions and decisions they change |
| Gotchas | | ✓ nodes in #157; this file links them |
| Branch state, what is in flight | git + PR body (from case lines) | ✓ (a `genre=hint` seed of a transformation) |
| Methodology, ontology | | ✓ |
| Decisions | | ✓ (a node, at once) |
| Questions of substance, commitments | | ✓ (vimarshas) |
| Plans | | ✓ (transformation map) |
| One-off task, progress, handover | | ✓ (case journal) |
| Commit history, PRs, SHAs | git | (never in the graph) |

**No `HANDOVER.md`**: branch state has homes — `git branch`/`log` and the open PR body, node modes, the transformation seed; a handwritten file is the only one of them that lies silently.

## Commands
| Command | What it does |
|---|---|
| `make sync` | install deps (PrismQL editable from `../../vibes/prismql`) |
| `make serve` | query server on :8931 for every corpus in `prismql.toml` (board at `/board/`) |
| `make repl` | interactive queries on the default corpus |
| `make smoke` | two known counts on the wiki stream against a running server: 25 restores within 10 minutes, 47 same-label restores within a day |
| `make check` | the gate: full ruff + format on `prepare/`, pyflakes on `runs/`, smoke if the server is up |
| `make village` | AI Village export (`data/village/`) → `data/village.parquet` without embeddings |
| `make wiki-data` | the public collusion.wiki export → `data/collusion_wiki/` (network; skips files already there) |
| `make wiki` | export → `data/collusion_wiki_events.jsonl` + `data/collusion_wiki_revisions.jsonl` (corpora `wiki`, `revisions`) |
| `make urlquery ZIP=…` | Transluce release zip (downloaded by hand) → `data/transluce/urlquery.parquet` |
| `make journal` | the server's query journal → `logs/server-journal.jsonl` (published; no event contents) |
| `make wiki-msgs` | collusion.wiki export → `data/wiki_msgs.parquet`: one row per text a save added or removed (from `hunks`), plus deletes, probes, reverts |
| `make explorer-fetch` | collusion.wiki explorer pages of the venues the download lacks → `data/collusion_explorer/` (network; cached; 1.5 s between requests) |
| `make swarm-msgs` | `wiki_msgs` + the explorer's timed rows from other venues → `data/swarm_msgs.parquet` |

- Query the server signed: header `X-PrismQL-Client: claude` (or your own name) and a `"label"` on anything worth finding again; `runs/ask.py CORPUS < queries` does both and prints `warnings`. Read `warnings` before reporting a number.
- The query method: `.claude/skills/prismql/SKILL.md` — `GET /schema` first, then `POST /evaluate`; totals via `AGGREGATE count()`; big result sets via `"output": "file"` (files land in `results/`). Language cheat sheet: `../../vibes/prismql/docs/MENTAL_MODEL.md`.
- Embeddings for Village (`data/village.parquet`, embeddinggemma-300m, 768-d) are built on a GPU machine: `prepare/embed/build_emb.py` + `embed_client.py` against a vLLM container; the query prefix is stamped in the Parquet metadata and applied by the server.

## Project structure
| Path | What |
|---|---|
| `prepare/` | data pipeline: export tables → one stream per corpus (`village.py`, `wiki_events.py`, `urlquery.py`, `uq_wiki.py`, `wiki_msgs.py`, `explorer_sites.py`, `swarm_msgs.py`, `textkey.py`; `embed/` — embedding run) |
| `runs/` | exploratory query and analysis scripts (null twins, lag profiles, mention graph, embedding evals) |
| `notes/` | findings by day — the record of what was found and its limits |
| `keenable/` | SQL of public-page searches (Keenable SELECT) |
| `data/` | corpora and raw exports — gitignored; shared with the team via Drive |
| `results/` | query outputs, caches, server journal — gitignored |
| `prismql.toml` | server config: one `[corpora.<name>]` section per stream (both timestamp keys), dictionaries, board fields |
| `.claude/skills/prismql/` | the PrismQL query skill (symlink) |
| `REALITY.md` | claim carriers |

## Code conventions
- **Meaning lives in the graph, code references it**: a comment with a rationale, rejected alternatives or integration design is a node; in code — "(graph `@aleph/prismql`, node #N)". Mechanics — in words on the spot. Without graph access (Mermachine): write the rationale in `notes/` and link the note instead.
- A question is a shape in an ordered stream: then / near / same entity / never followed. Vary one token at a time.
- **Every count gets its null twin before it is called a finding**, and the twin must break exactly what is being tested (graph, #161).
- Data preparation lives in `prepare/` and is reproducible end to end; one-off analysis lives in `runs/`.
- Gotchas (graph `@aleph/prismql`): THOUGHT rows shift positional windows (#158); one `similar_to` threshold does not fit every question (#159); a wiki revision is the whole page, not a message (#160); the null twin must break what is tested (#161); village goals change weekly — compare within a goal and a regime (#162).
- **Test discipline**: none for exploratory runs; the gate covers lint and format of the pipeline plus the server smoke.

## What to update when
- `AGENTS.md` — **what is knowable from a graph node is not written here**; it holds what is needed before an agent reaches the graph (commands, entry into orientation, invariants outside the linter, stop-forks), and changes when that changes.
- `REALITY.md` — when a claim class's carrier appears, changes, or turns out unreachable; dated measurements go to the graph or `notes/`.
- `notes/` — the day a finding (or a negative result) is made.
- `prismql.toml` — a new corpus or dictionary; both timestamp keys on every corpus.
- The project graph — every merge (Session lifecycle).

## Git workflow
- **Conventional commits** (`feat:`/`fix:`/`chore:`/`refactor:`/`docs:`/`test:`); branches `feat/…`, `fix/…`, `chore/…`; PR titles in the same format.
- **Commit trailers**: keep the `Co-Authored-By` / `Claude-Session` lines the harness adds — the history carries them.
- **Gate — one call**: `make check`; call it by name, do not assemble the steps by hand.
- **`WRITEUP.md` is written by humans only** (the hackathon writeup, checked with Pangram; graph #166): agents never write, edit, reformat or commit changes to it — a hook blocks Write/Edit. Agents may read it, and give ideas, facts, numbers and code examples in chat, notes or PR bodies, never prose for it.
- **Never commit data**: `data/`, `results/` and exports stay gitignored; they travel via `gdrive:swarmchasing/`. Never commit keys or service tokens.
- **Forge**: GitHub, CLI `gh` (`gh pr create`, `gh pr checks <n> --watch`); a branch per change, and a pushed branch gets a PR in the same move.
- **Definition of done**: a finding is written in `notes/` with its query, count and null twin; code is merged into `master` with `make check` green.
- **Never** `--no-verify`, `--force`, `--no-gpg-sign`, `git reset --hard` without an explicit instruction.

*(iskronify: contract `16`, stamp `2026-09-29` — offer a rerun when the installed iskronify's description names a higher contract or when the sources this file was derived from moved after this date.)*
