const BASE = ''

export async function getInsights() {
  const res = await fetch(`${BASE}/api/insights`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Failed to fetch insights: ${res.status}`)
  return res.json()
}

export async function getHistory() {
  const res = await fetch(`${BASE}/api/insights/history`)
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`)
  return res.json()
}

export async function runPipeline() {
  const res = await fetch(`${BASE}/api/run`, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to start pipeline: ${res.status}`)
  return res.json()
}

export async function approve() {
  const res = await fetch(`${BASE}/api/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error(`Approve failed: ${res.status}`)
  return res.json()
}