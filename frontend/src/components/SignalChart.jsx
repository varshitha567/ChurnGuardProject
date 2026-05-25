import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Cell, ResponsiveContainer, LabelList,
} from 'recharts'
import { SIGNAL_META } from './utils'

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-stone-200 rounded-lg shadow-lg px-4 py-3 text-sm">
      <p className="font-semibold text-stone-900 mb-1">{d.label}</p>
      <p className="text-stone-500 text-xs">{d.description}</p>
      <div className="mt-2 pt-2 border-t border-stone-100 flex items-baseline gap-2">
        <span className="text-2xl font-bold" style={{ color: d.color }}>{d.count}</span>
        <span className="text-stone-400 text-xs">customers flagged</span>
      </div>
      <p className="text-xs text-stone-400 mt-1">{d.pct}% of portfolio</p>
    </div>
  )
}

export default function SignalChart({ signalCounts, onBarClick, activeSignal }) {
  const data = Object.entries(SIGNAL_META).map(([key, meta]) => ({
    key,
    label: meta.label,
    description: meta.description,
    count: signalCounts[key] ?? 0,
    color: meta.color,
    pct: (((signalCounts[key] ?? 0) / 1000) * 100).toFixed(1),
  }))

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-stone-900">Signal Distribution</h2>
        <p className="text-sm text-stone-400 mt-0.5">
          Customers flagged per churn signal — click a bar to view analysis
        </p>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 60, left: 8, bottom: 0 }}
          barCategoryGap="28%"
        >
          <CartesianGrid horizontal={false} stroke="#f5f5f4" />
          <XAxis
            type="number"
            domain={[0, 450]}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12, fill: '#a8a29e' }}
          />
          <YAxis
            dataKey="label"
            type="category"
            width={148}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 13, fill: '#57534e', fontWeight: 500 }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#fef9c3', radius: 4 }} />
          <Bar
            dataKey="count"
            radius={[0, 6, 6, 0]}
            cursor="pointer"
            onClick={(d) => onBarClick(d.key)}
          >
            {data.map((entry) => (
              <Cell
                key={entry.key}
                fill={entry.color}
                opacity={!activeSignal || activeSignal === entry.key ? 1 : 0.35}
              />
            ))}
            <LabelList
              dataKey="count"
              position="right"
              style={{ fontSize: 13, fontWeight: 600, fill: '#57534e' }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}