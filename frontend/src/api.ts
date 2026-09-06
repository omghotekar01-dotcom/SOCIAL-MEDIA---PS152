import type { Alert, DashboardBundle, Demographics, Evidence, EventItem, Narrative, NetworkData, Summary, Trend } from './types'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`${response.status} ${response.statusText}: ${body.slice(0, 300)}`)
  }
  return response.json() as Promise<T>
}

export async function loadDashboard(): Promise<DashboardBundle> {
  const [summary, narratives, trends, network, demographics, evidence, alerts, events, platformStatus] = await Promise.all([
    request<Summary>('/api/dashboard/summary'),
    request<Narrative[]>('/api/narratives'),
    request<Trend[]>('/api/trends'),
    request<NetworkData>('/api/network'),
    request<Demographics>('/api/demographics'),
    request<Evidence>('/api/evidence'),
    request<Alert[]>('/api/alerts'),
    request<EventItem[]>('/api/events?limit=1000'),
    request<Record<string, unknown>>('/api/platforms/status'),
  ])
  return { summary, narratives, trends, network, demographics, evidence, alerts, events, platformStatus }
}

export async function seedDemo(): Promise<{ ingested: number; summary: Summary }> {
  return request('/api/demo/seed', {
    method: 'POST',
    body: JSON.stringify({ reset: true }),
  })
}

export async function ingestX(query: string): Promise<Record<string, unknown>> {
  return request('/api/ingest/x/search', {
    method: 'POST',
    body: JSON.stringify({ query, max_results: 20 }),
  })
}

export async function importXUrl(url: string): Promise<Record<string, unknown>> {
  return request('/api/ingest/x/url', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export async function ingestTelegram(): Promise<Record<string, unknown>> {
  return request('/api/ingest/telegram/poll', {
    method: 'POST',
    body: JSON.stringify({ max_updates: 50 }),
  })
}

export async function ingestYouTube(query: string): Promise<Record<string, unknown>> {
  return request('/api/ingest/youtube/search', {
    method: 'POST',
    body: JSON.stringify({ query, max_videos: 3, max_comments_per_video: 20 }),
  })
}

export function exportCsvUrl(): string {
  return `${API_BASE}/api/export/events.csv`
}
