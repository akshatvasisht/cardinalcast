import type {
  TokenResponse,
  User,
  Wager,
  PlaceWagerBody,
  PlaceWagerResponse,
  OddsOption,
  LeaderboardEntry,
  DailyStatusResponse,
  DailyClaimResponse,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const HEADERS = {
  CONTENT_TYPE: 'application/json',
  AUTHORIZATION: 'Authorization',
}

function getHeaders(token: string | null): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': HEADERS.CONTENT_TYPE,
  }
  if (token) {
    headers[HEADERS.AUTHORIZATION] = `Bearer ${token}`
  }
  return headers
}

async function handleResponse<T>(res: Response): Promise<T> {
  const text = await res.text()
  const data = text ? (JSON.parse(text) as T) : ({} as T)
  if (!res.ok) {
    const detail = (data as { detail?: string })?.detail
    throw new Error(typeof detail === 'string' ? detail : res.statusText)
  }
  return data
}

export const api = {
  async register(username: string, password: string): Promise<TokenResponse> {
    const res = await fetch(`${BASE}/auth/register`, {
      method: 'POST',
      headers: getHeaders(null),
      body: JSON.stringify({ username, password }),
    })
    return handleResponse<TokenResponse>(res)
  },

  async login(username: string, password: string): Promise<TokenResponse> {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: getHeaders(null),
      body: JSON.stringify({ username, password }),
    })
    return handleResponse<TokenResponse>(res)
  },

  async me(token: string): Promise<User> {
    const res = await fetch(`${BASE}/auth/me`, {
      headers: getHeaders(token),
    })
    return handleResponse<User>(res)
  },

  async listWagers(token: string): Promise<Wager[]> {
    const res = await fetch(`${BASE}/wagers`, { headers: getHeaders(token) })
    return handleResponse<Wager[]>(res)
  },

  async placeWager(token: string, body: PlaceWagerBody): Promise<PlaceWagerResponse> {
    const res = await fetch(`${BASE}/wagers`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify(body),
    })
    return handleResponse<PlaceWagerResponse>(res)
  },

  async listOdds(params?: { forecast_date?: string; target?: string }): Promise<OddsOption[]> {
    const sp = new URLSearchParams()
    if (params?.forecast_date) sp.set('forecast_date', params.forecast_date)
    if (params?.target) sp.set('target', params.target)
    const qs = sp.toString()
    const url = qs ? `${BASE}/odds?${qs}` : `${BASE}/odds`
    const res = await fetch(url)
    return handleResponse<OddsOption[]>(res)
  },

  async dailyStatus(token: string): Promise<DailyStatusResponse> {
    const res = await fetch(`${BASE}/daily/status`, { headers: getHeaders(token) })
    return handleResponse<DailyStatusResponse>(res)
  },

  async dailyClaim(token: string): Promise<DailyClaimResponse> {
    const res = await fetch(`${BASE}/daily/claim`, {
      method: 'POST',
      headers: getHeaders(token),
    })
    return handleResponse<DailyClaimResponse>(res)
  },

  async leaderboard(): Promise<LeaderboardEntry[]> {
    const res = await fetch(`${BASE}/leaderboard/`)
    return handleResponse<LeaderboardEntry[]>(res)
  },
  async previewOverUnder(
    token: string,
    params: { forecast_date: string; target: string; direction: string; predicted_value: number }
  ): Promise<{ multiplier: number }> {
    const sp = new URLSearchParams()
    sp.set('forecast_date', params.forecast_date)
    sp.set('target', params.target)
    sp.set('direction', params.direction)
    sp.set('predicted_value', String(params.predicted_value))
    const res = await fetch(`${BASE}/wagers/preview?${sp.toString()}`, {
      headers: getHeaders(token),
    })
    return handleResponse<{ multiplier: number }>(res)
  },
}
