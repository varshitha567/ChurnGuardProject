import { formatTimestamp } from './utils'

export default function RunHistory({ history }) {
  if (!history.length) return null

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <h2 className="text-base font-semibold text-stone-900 mb-4">Run History</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-stone-100">
              <th className="text-left text-xs font-medium text-stone-400 uppercase tracking-wide pb-3 pr-8">Run</th>
              <th className="text-left text-xs font-medium text-stone-400 uppercase tracking-wide pb-3">Timestamp</th>
              <th className="text-left text-xs font-medium text-stone-400 uppercase tracking-wide pb-3">File</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-50">
            {history.map((item, i) => (
              <tr key={item.key} className="hover:bg-stone-50 transition-colors">
                <td className="py-3 pr-8">
                  <div className="flex items-center gap-2">
                    {i === 0 && (
                      <span className="text-xs font-medium text-brand-700 bg-brand-50 border border-brand-200 px-2 py-0.5 rounded-full">
                        Latest
                      </span>
                    )}
                    {i > 0 && (
                      <span className="text-xs text-stone-400">#{history.length - i}</span>
                    )}
                  </div>
                </td>
                <td className="py-3 text-stone-700 font-medium">{formatTimestamp(item.timestamp)}</td>
                <td className="py-3 text-stone-400 font-mono text-xs">{item.key}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}