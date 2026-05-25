export default function Header({ runTimestamp, threadId, onRefresh, loading, pipelineRunning }) {
  const formatted = runTimestamp
    ? new Date(runTimestamp).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    : null

  return (
    <header className="bg-white border-b border-stone-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <div className="w-3 h-3 bg-white rounded-full" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-stone-900 leading-none">ChurnGuard</h1>
            <p className="text-xs text-stone-400 mt-0.5 leading-none">Retention Intelligence Platform</p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {formatted && (
            <div className="text-right hidden sm:block">
              <p className="text-xs text-stone-400 leading-none mb-1">Last pipeline run</p>
              <p className="text-sm font-medium text-stone-700">{formatted}</p>
            </div>
          )}
          {threadId && (
            <div className="text-right hidden md:block">
              <p className="text-xs text-stone-400 leading-none mb-1">Run ID</p>
              <p className="text-xs font-mono text-stone-500">{threadId}</p>
            </div>
          )}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded-lg hover:bg-brand-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg
              className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {pipelineRunning ? 'Running...' : 'Refresh'}
          </button>
        </div>
      </div>
    </header>
  )
}