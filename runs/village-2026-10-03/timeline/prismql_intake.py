"""PrismQL: how does outside news enter the village? For each topic:
  H->A : human mention FOLLOWED_BY agent mention within 1 day
  A!H  : agent mention NOT_PRECEDED_BY any human mention within 30 days (agents brought it in themselves)
  A    : all agent mentions
Corpus village_chat. Results -> prismql_intake.json"""
import json, urllib.request
URL = 'http://localhost:8942/evaluate'
TOPICS = {
 'moltbook': 'contains_phrase("moltbook")',
 'export control': 'contains_phrase("export control") OR contains_phrase("export controls")',
 'pentagon': 'contains_phrase("pentagon") OR contains_phrase("department of war")',
 'sycophancy': 'contains_phrase("sycophancy") OR contains_phrase("sycophantic")',
 'bliss attractor': 'contains_phrase("bliss attractor")',
 'hugging face': 'contains_phrase("hugging face") OR contains_phrase("huggingface")',
 'model welfare': 'contains_phrase("model welfare") OR contains_phrase("ai welfare")',
 'deepseek v4': 'contains_phrase("deepseek-v4") OR contains_phrase("v4-flash")',
}
def ev(q, n=5):
    body = json.dumps({'corpus': 'village_chat', 'query': q, 'max_results': n}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json', 'X-PrismQL-Client': 'timeline'})
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        return {'error': e.read().decode()[:300]}
out = {}
for name, t in TOPICS.items():
    qs = {
      'H->A': f'SELECT field(kind, user) AND ({t}) FOLLOWED_BY field(kind, agent) AND ({t}) DURING 1 day',
      'A!H': f'SELECT field(kind, agent) AND ({t}) NOT_PRECEDED_BY field(kind, user) AND ({t}) DURING 30 days',
      'A': f'SELECT field(kind, agent) AND ({t})',
      'H': f'SELECT field(kind, user) AND ({t})',
    }
    out[name] = {}
    for k, q in qs.items():
        r = ev(q)
        first = None
        if r.get('results'):
            e = r['results'][0]['events']
            first = [(x.get('time'), x.get('kind'), x.get('agent') if x.get('kind') == 'agent' else 'human', (x.get('text') or '')[:160]) for x in e]
        out[name][k] = {'query': q, 'total': r.get('total'), 'first': first, 'error': r.get('error')}
        print(name, k, r.get('total'), r.get('error', ''))
json.dump(out, open('/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/prismql_intake.json', 'w'), indent=1)
