import { SIGNAL_META } from './utils'

export default function KpiCards({ signalCounts }) {
  const entries = Object.entries(SIGNAL_META)
  const total = Object.values(signalCounts).reduce((s, n) => s + n, 0)

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
      <div className="bg-white rounded-xl border border-stone-200 p-5">
        <p className="text-xs font-medium text-stone-400 uppercase tracking-wide">Total Flags</p>
        <p className="text-3xl font-bold text-stone-900 mt-1">{total.toLocaleString()}</p>
        <p className="text-xs text-stone-400 mt-1">across all signals</p>
      </div>

      {entries.map(([key, meta]) => (
        <div key={key} className="bg-white rounded-xl border border-stone-200 p-5">
          <p className="text-xs font-medium text-stone-400 uppercase tracking-wide truncate">
            {meta.short}
          </p>
          <p className="text-3xl font-bold mt-1" style={{ color: meta.color }}>
            {(signalCounts[key] ?? 0).toLocaleString()}
          </p>
          <p className="text-xs text-stone-400 mt-1">customers</p>
        </div>
      ))}
    </div>
  )
}