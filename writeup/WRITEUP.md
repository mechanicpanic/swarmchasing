
Chat logs are long ordered streams of data. LLMs usually grep their way through them, spilling bits and pieces as they go. It seems only fair to try and give them something better suited for logs that regex matching  something like SQL, EQL or Flink. What happens if you also make it human-readable enough without Senior SQL Analyst experience? Mermachine and Anna tried to find out :)
## Tool: PrismQL, agentic skills and observability GUI

PrismQL was born a long time ago out of an undergrad research project intended to help *humans* query and disentangle long chat logs without uncertainty. It matched words and precomputed features in a stream of chat messages and returned long, ordered groups with gaps in them. 

In 2025-2026, **Anna** rewrote PrismQL in Python, intending to adapt it for semi-automatic experimentation loops with agents. For the hackathon, she built the **live GUI board** that logs both the queries with their origin (human, agent) and the results for oversight and analysis, as well as the agent skills for the language and investigation.

**Mermachine** was the first human to use the language independently to carry out a successful slopvestigation with her Claude. She also built the **Review and Trails tool**, and helped Anna with bugs and problematic design decisions of PrismQL.

During the hackathon, we devised a preliminary workflow for better slopvestigations, run a novel reporting benchmark augmented with PrismQL, and found some really silly stuff models said and did. We publish our results and demo here: **mechanicpanic/swarmchasing.**
### The language, the server and the boards

PrismQL (*Pattern Recognition in Sequential Messages*), in general, describes repeatable shapes in streams of events: *action A by agent X followed by message similar to "I'm worried" from agent Y during 10 minutes*. It matches words in messages, values in fields, semantic similarity of a message to a phrase, supports subqueries, runs of repeated operators,  Very importantly, it doesn't pre-aggregate the results.

An example query on AI Village:

```
SELECT field(kind, REQUEST_HUMAN_HELPER) AND field(agent, $a)
       NOT_FOLLOWED_BY field(kind, CANCEL_REQUEST_FOR_HUMAN_HELPER) AND field(agent, $a)
       DURING 1 hour
```

The server is a simple HTTP server that loads the ingested datasets, precomputed embeddings, and an inverted index. The necessary schema is id, timestamp and optionally, text. Its endpoints are `/evaluate` — runs a PrismQL query with validation; `/search` — full-text search; and `/similar` — semantic search. The latter two are intended to give agents well-built exploratory tools since they rarely reach for them otherwise.

The live GUI board is the observability watchtower for PrismQL use. It logs all sent queries and displays the group results as readable visual chains; it also retains all necessary information (query source, word lists, and so on). It doesn't hold the actual hypothesis loop; the Review and Trails tool does and it's the experimentation workplace.
## Workflow

## Findings (optional)
### The wiki swarm
### A mailing list that never existed
### Fair dice in private, hidden 1s in public
### A licence to suspect
### "PR #397 does not exist"
