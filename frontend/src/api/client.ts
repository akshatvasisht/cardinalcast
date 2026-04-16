import type {
  TokenResponse,
  User,
  Wager,
  PlaceWagerBody,
  PlaceWagerResponse,
  OddsOption,
  LeaderboardResponse,
  DailyStatusResponse,
  DailyClaimResponse,
} from './types'
import {
  MOCK_USER,
  MOCK_WAGERS,
  MOCK_ODDS,
  MOCK_LEADERBOARD,
  MOCK_DAILY_STATUS,
  MOCK_DAILY_CLAIM,
} from './mock'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const DEV_BYPASS = import.meta.env.DEV && import.meta.env.VITE_DEV_BYPASS_AUTH === 'true'
const BYPASS = 'dev-bypass'
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
    if (token === BYPASS) return { ...MOCK_USER }
    const res = await fetch(`${BASE}/auth/me`, { headers: getHeaders(token) })
    return handleResponse<User>(res)
  },

  async listWagers(token: string): Promise<Wager[]> {
    if (token === BYPASS) return [...MOCK_WAGERS]
    const res = await fetch(`${BASE}/wagers`, { headers: getHeaders(token) })
    return handleResponse<Wager[]>(res)
  },

  async placeWager(token: string, body: PlaceWagerBody): Promise<PlaceWagerResponse> {
    if (token === BYPASS) return { id: 99, status: 'PENDING', message: 'Mock wager placed.' }
    const res = await fetch(`${BASE}/wagers`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify(body),
    })
    return handleResponse<PlaceWagerResponse>(res)
  },

  async listOdds(params?: { forecast_date?: string; target?: string }): Promise<OddsOption[]> {
    if (DEV_BYPASS) {
      let odds = [...MOCK_ODDS]
      if (params?.forecast_date) odds = odds.filter(o => o.forecast_date === params.forecast_date)
      if (params?.target) odds = odds.filter(o => o.target === params.target)
      return odds
    }
    const sp = new URLSearchParams()
    if (params?.forecast_date) sp.set('forecast_date', params.forecast_date)
    if (params?.target) sp.set('target', params.target)
    const qs = sp.toString()
    const url = qs ? `${BASE}/odds?${qs}` : `${BASE}/odds`
    const res = await fetch(url)
    return handleResponse<OddsOption[]>(res)
  },

  async dailyStatus(token: string): Promise<DailyStatusResponse> {
    if (token === BYPASS) return { ...MOCK_DAILY_STATUS }
    const res = await fetch(`${BASE}/daily/status`, { headers: getHeaders(token) })
    return handleResponse<DailyStatusResponse>(res)
  },

  async dailyClaim(token: string): Promise<DailyClaimResponse> {
    if (token === BYPASS) return { ...MOCK_DAILY_CLAIM }
    const res = await fetch(`${BASE}/daily/claim`, {
      method: 'POST',
      headers: getHeaders(token),
    })
    return handleResponse<DailyClaimResponse>(res)
  },

  async leaderboard(token?: string | null): Promise<LeaderboardResponse> {
    if (DEV_BYPASS) return { ...MOCK_LEADERBOARD, top: [...MOCK_LEADERBOARD.top] }
    const res = await fetch(`${BASE}/leaderboard/`, {
      headers: token ? getHeaders(token) : {},
    })
    return handleResponse<LeaderboardResponse>(res)
  },

  async previewOverUnder(
    token: string,
    params: { forecast_date: string; target: string; direction: string; predicted_value: number }
  ): Promise<{ multiplier: number }> {
    if (token === BYPASS) return { multiplier: 2.4 }
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
