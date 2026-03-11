import { useEffect, useState } from "react"
import { X } from "lucide-react"
import { api } from "@/api"
import type { Book, ArcPoint } from "@/api"
import { BookCard } from "@/components/BookCard"
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Legend,
} from "recharts"

const COLORS = ["#f59e0b", "#3b82f6", "#22c55e", "#ec4899"]

function mergeArcs(arcs: Record<string, ArcPoint[]>): any[] {
  const allPositions = Array.from(
    new Set(Object.values(arcs).flatMap(a => a.map(d => d.position_pct)))
  ).sort((a, b) => a - b)

  return allPositions.map(pos => {
    const point: any = { position_pct: pos }
    for (const [bookId, arc] of Object.entries(arcs)) {
      const closest = arc.reduce((prev, curr) =>
        Math.abs(curr.position_pct - pos) < Math.abs(prev.position_pct - pos) ? curr : prev
      )
      point[bookId] = closest.tension_score
    }
    return point
  })
}

export function Compare() {
  const [books, setBooks] = useState<Book[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [arcs, setArcs] = useState<Record<string, ArcPoint[]>>({})
  const [titles, setTitles] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [comparing, setComparing] = useState(false)
  const [chartData, setChartData] = useState<any[]>([])

  useEffect(() => {
    api.books({ limit: 48 }).then(data => {
      setBooks(data)
      const t: Record<string, string> = {}
      data.forEach(b => { t[b.book_id] = b.title })
      setTitles(t)
      setLoading(false)
      data.forEach(book => {
        api.arc(book.book_id).then(arc => {
          setArcs(prev => ({ ...prev, [book.book_id]: arc }))
        }).catch(() => {})
      })
    })
  }, [])

  const toggle = (id: string) => {
    setSelected(prev =>
      prev.includes(id)
        ? prev.filter(x => x !== id)
        : prev.length < 4 ? [...prev, id] : prev
    )
  }

  const runCompare = async () => {
    if (selected.length < 2) return
    setComparing(true)
    const data = await api.compare(selected)
    setChartData(mergeArcs(data))
    setComparing(false)
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-8">
      <div>
        <p className="label mb-2">Compare Mode</p>
        <h1 className="font-serif text-4xl text-text">Side by Side</h1>
        <p className="mt-2 text-subtle">Select 2–4 books to overlay their tension curves.</p>
      </div>

      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {selected.map((id, i) => (
            <div
              key={id}
              className="flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-full text-sm border"
              style={{ borderColor: COLORS[i] + "60", background: COLORS[i] + "15", color: COLORS[i] }}
            >
              <span className="max-w-[180px] truncate">{titles[id]}</span>
              <button onClick={() => toggle(id)} className="opacity-60 hover:opacity-100">
                <X size={12} />
              </button>
            </div>
          ))}
          {selected.length >= 2 && (
            <button
              onClick={runCompare}
              disabled={comparing}
              className="btn-primary ml-2"
            >
              {comparing ? "Loading…" : "Compare"}
            </button>
          )}
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="card p-5">
          <h2 className="label mb-4">Tension Overlay</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c1c28" vertical={false} />
              <XAxis
                dataKey="position_pct"
                tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: "#6b6b80", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tickFormatter={v => `${(v * 100).toFixed(0)}`}
                tick={{ fill: "#6b6b80", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: "#111118", border: "1px solid #1c1c28", borderRadius: 8, fontSize: 12 }}
                labelFormatter={v => `${(Number(v) * 100).toFixed(1)}% through book`}
              />
              <Legend
                formatter={id => (
                  <span className="text-xs text-subtle">
                    {titles[id]?.slice(0, 30) ?? id}
                  </span>
                )}
                wrapperStyle={{ paddingTop: 12 }}
              />
              {selected.map((id, i) => (
                <Line
                  key={id}
                  type="monotone"
                  dataKey={id}
                  stroke={COLORS[i]}
                  strokeWidth={2}
                  dot={false}
                  name={id}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Book picker */}
      <div>
        <p className="label mb-4">
          {selected.length === 0
            ? "Pick books to compare"
            : `${selected.length}/4 selected`}
        </p>
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="card h-40 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {books.map(book => (
              <BookCard
                key={book.book_id}
                book={book}
                arc={arcs[book.book_id] ?? []}
                selected={selected.includes(book.book_id)}
                onSelect={() => toggle(book.book_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
