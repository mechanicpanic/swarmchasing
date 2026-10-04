
Chat logs are long ordered streams of data. LLMs usually grep their way through them, spilling bits and pieces as they go. It seems only fair to try and give them something better suited for logs that regex matching --- something like SQL, EQL or Flink. What happens if you also make it human-readable enough without Senior SQL Analyst experience? Mermachine and Anna tried to find out :)
## Tool: PrismQL, agentic skills and observability GUI

PrismQL was born a long time ago out of an undergrad research project intended to help *humans* query and disentangle long chat logs without uncertainty. It matched words and precomputed features in a stream of chat messages and returned long, ordered groups with gaps in them. 

In 2025-2026, **Anna** rewrote PrismQL in Python, intending to adapt it for semi-automatic experimentation loops with agents. For the hackathon, she built the **live GUI board** that logs both the queries with their origin (human, agent) and the results for oversight and analysis, as well as the agent skills for the language and investigation.

**Mermachine** was the first human to use the language independently to carry out successful slopvestigations with her Claude on both the AI Village and Collusion wiki datasets. She also built the **Review and Trails tool**, and helped Anna with bugs and problematic design decisions of PrismQL.

During the hackathon, we devised a preliminary workflow for better slopvestigations, run a novel reporting benchmark augmented with PrismQL, and found some really silly stuff models said and did. We publish our results and demo here: [**mechanicpanic/swarmchasing.**](https://github.com/mechanicpanic/swarmchasing)
### The language, the server and the boards

PrismQL (*Pattern Recognition in Sequential Messages*), in general, describes repeatable shapes in streams of events: *action A by agent X followed by message similar to "I'm worried" from agent Y during 10 minutes*. It matches words in messages, values in fields, semantic similarity of a message to a phrase, supports subqueries, runs of repeated operators, and variable binding.  It doesn't pre-aggregate the results and returns them hydrated.

An example query on AI Village:

```
SELECT field(kind, REQUEST_HUMAN_HELPER) AND field(agent, $a)
       NOT_FOLLOWED_BY field(kind, CANCEL_REQUEST_FOR_HUMAN_HELPER) AND field(agent, $a)
       DURING 1 hour
```

The server is a simple HTTP server that loads the ingested datasets, precomputed embeddings, and full-text search. The necessary schema is id, timestamp and optionally, text, and it exposes three endpoints: /evaluate for PrismQL queries; /search for tantivy-based full-text search; and /similar which is embedding-based search. The latter two are intended to give agents ready-made exploratory tools since they rarely reach for them spontaneously.

The dashboard is the "low-level" observability for PrismQL. It logs all sent queries and displays the group results as chains; it also shows all necessary information (query source, word lists, and so on). It doesn't hold the actual hypothesis loop, however. The Review and Trails tool does and it's the experimentation workspace.
## Workflow and hackathon experience :)

We've tried many things during the weekend, and quickly found that having just an observability board is not enough: there needs to be at least a basic space to record your hypotheses and test the queries aganst them, even if Claude is the one writing. This is what we tentatively refer to as the "manual workflow".

Mermachine was chasing down questions in the Collusion wiki export; for this, she implemented an auxiliary tool with two purposes. In the Review part of it, the user writes down a question they want to investigate (e.g., **a signed text ('-- name') — is it addressed to other agents?**), run a query against it and annotate or just make note whether it makes sense at all. The Trails screen allows to save chains of questions in the investigation with their answers. This is how she investigated the question of June 18th Collusion wiki activity: first, manually sifting through data to find anomalies, running into the June 18th 311 pages with the same text, asking questions and follow-up questions and pinning them to the board. Mermachine found out that agents have identity issues: the spike seemed to be looping behaviour of one agent, but there are 58 names in total in the text. 

Manual work with PrismQL is the hardest in hypothesis nomination --- whether swarms exhibit any kind of regular shapes in their logs that can't be found otherwise. They do, but this fine-grained analysis is hard: humans don't natively think in such shapes. The agents might, however, so we also let them work autonomously, as follows: they proposed questions using the `/search` and `/similar`, we manually approved some of them, and they ran a loop:

`write a query and run it->find patterns->shuffle the chat data and run the query again, many times->see whether the count of hits is about the same->give the claim to a verifier agent who replicates it and settles whether it holds or not`.

Our repo holds the results and the first version of the agentic skill that followed.

## Conclusion

We see a lot of potential in this tool for people who like going on deep dives in weird logs. The next steps would be to make a unified workspace out of the two GUI tools and let agents access it too, with some kind of version history so they can be "held accountable", and to develop the language further. 

We think that even though thinking in ordered log-shapes is harder than thinking in greppable narratives, the shapes are less likely to lie. Especially with human observation. The shuffle test methodology is surprisingly fitting here, too, as many proposed hypotheses didn't hold under it despite sounding believable at first. 

We also found out that append-only logs suck! They're confusing for humans and for agents. Better recording and memory systems will probably be the next big step for slopvestigations.

Finally, we've had a lot of fun and tried out a novel asynchronous hackathon methodology since Anna is on European time: openclaws pinging claude code sessions from a discord server :) 
