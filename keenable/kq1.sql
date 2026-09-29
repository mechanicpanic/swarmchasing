SELECT
  url,
  published_at,
  UNNEST(
    SEM_EXTRACT_ALL(
      content,
      'a specific incident in which AI agents took unauthorized actions on the public internet',
      incident_date := 'date the agents acted, YYYY-MM-DD',
      target := 'organization, website or service the agents acted on',
      channel := 'the service or trick the agents used to reach the internet or the target',
      attributed_to := 'AI lab or model the page attributes the agents to',
      evidence := 'per_field'
    ),
    recursive := true
  )
FROM WEB_SEARCH(
  'OpenAI agents escaped sandbox incident report',
  'rogue AI agent swarm Hugging Face attack details',
  'Transluce urlquery agent activity government website',
  'AI agent DNS sandbox escape public chatbot',
  'OpenAI misalignment report agents unauthorized internet access',
  'Australian Institute of Health and Welfare AI agents bypassed anti-bot',
  'AI agents link shortener payloads swarmtraces',
  'site:alignment.openai.com misalignment reports',
  published_after := '2026-07-01'
)
WHERE SEM_MATCH(content, 'describes a specific incident of AI agents acting outside their sandbox or without authorization')
