const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export interface Book {
  book_id: string
  title: string
  author: string | null
  subjects: string[]
  language: string | null
  publish_year: number | null
  word_count: number | null
}

export interface ArcPoint {
  chunk_index: number
  position_pct: number
  chapter: string | null
  word_count: number | null
  sentiment_score: number
  tension_score: number
  pacing_score: number
  conflict_density: number
  dominant_characters: string[]
}

export interface Character {
  character_name: string
  mention_count: number
  first_appearance_pct: number
  last_appearance_pct: number
  peak_presence_pct: number
}

export interface GenreStat {
  subject: string
  avg_tension: number
  avg_sentiment: number
  avg_pacing: number
  book_count: number
}

export const api = {
  books: (params?: { limit?: number; offset?: number; author?: string; language?: string }) => {
    const q = new URLSearchParams()
    if (params?.limit)    q.set("limit",    String(params.limit))
    if (params?.offset)   q.set("offset",   String(params.offset))
    if (params?.author)   q.set("author",   params.author)
    if (params?.language) q.set("language", params.language)
    return get<Book[]>(`/api/books?${q}`)
  },

  book: (id: string) => get<Book>(`/api/books/${id}`),

  arc: (id: string) => get<ArcPoint[]>(`/api/books/${id}/arc`),

  characters: (id: string) => get<Character[]>(`/api/books/${id}/characters`),

  compare: (ids: string[]) =>
    get<Record<string, ArcPoint[]>>(`/api/compare?ids=${ids.join(",")}`),

  genres: () => get<GenreStat[]>("/api/explore/genres"),
}
