import { useState, useEffect, useCallback, useRef } from 'react'
import { getInsights, getHistory, runPipeline } from './api/client'
import Header from './components/Header'
import KpiCards from './components/KpiCards'
import SignalChart from './components/SignalChart'
import SignalCard from './components/SignalCard'
import SummaryPanel from './components/SummaryPanel'
import ApprovePanel from './components/ApprovePanel'
import RunHistory from './components/RunHistory'

function Skeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-stone-200 rounded-xl h-24" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-stone-200 rounded-xl h-72" />
        <div className="bg-stone-200 rounded-xl h-72" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-stone-200 rounded-xl h-20" />
        ))}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <div className="w-16 h-16 rounded-2xl bg-brand-100 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-stone-900 mb-2">No pipeline results yet</h3>
      <p className="text-sm text-stone-400 max-w-sm">
        Click <span className="font-medium text-brand-600">Refresh</span> in the header to run the signal pipeline and generate churn analysis.
      </p>
    </div>
  )
}

const POLL_INTERVAL = 15000

export default function App() {
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [error, setError] = useState(null)
  const [approveStatus, setApproveStatus] = useState('idle')
  const [activeSignal, setActiveSignal] = useState(null)
  const pollRef = useRef(null)
  const prevThreadRef = useRef(null)

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    setError(null)
    try {
      const [insights, hist] = await Promise.all([getInsights(), getHistory()])
      setData(insights)
      setHistory(hist)
      return insights
    } catch (e) {
      setError(e.message)
      return null
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  async function handleRefresh() {
    if (pipelineRunning) return

    setError(null)
    prevThreadRef.current = data?.thread_id ?? null

    try {
      setPipelineRunning(true)
      await runPipeline()

      // Poll every 15s until a new thread_id appears
      pollRef.current = setInterval(async () => {
        const fresh = await fetchData(true)
        if (fresh && fresh.thread_id !== prevThreadRef.current) {
          stopPolling()
          setPipelineRunning(false)
        }
      }, POLL_INTERVAL)

      // Safety cutoff at 8 minutes
      setTimeout(() => {
        if (pollRef.current) {
          stopPolling()
          setPipelineRunning(false)
          fetchData()
        }
      }, 480000)
    } catch (e) {
      setError(e.message)
      setPipelineRunning(false)
    }
  }

  useEffect(() => () => stopPolling(), [])

  function handleBarClick(signalKey) {
    setActiveSignal(prev => prev === signalKey ? null : signalKey)
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <Header
        runTimestamp={data?.run_timestamp}
        threadId={data?.thread_id}
        onRefresh={handleRefresh}
        loading={loading || pipelineRunning}
        pipelineRunning={pipelineRunning}
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl">
            {error} — make sure uvicorn is running on port 8000.
          </div>
        )}

        {pipelineRunning && (
          <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-xl flex items-center gap-3">
            <svg className="w-4 h-4 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Pipeline is running — analysing all 5 churn signals. Results will appear automatically in 2-3 minutes.
          </div>
        )}

        {loading && <Skeleton />}

        {!loading && !data && !error && <EmptyState />}

        {!loading && data && (
          <>
            <KpiCards signalCounts={data.signal_counts ?? {}} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <SignalChart
                  signalCounts={data.signal_counts ?? {}}
                  onBarClick={handleBarClick}
                  activeSignal={activeSignal}
                />
              </div>
              <div>
                <ApprovePanel status={approveStatus} onStatusChange={setApproveStatus} />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-stone-900">Signal Analysis</h2>
                {activeSignal && (
                  <button
                    onClick={() => setActiveSignal(null)}
                    className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                  >
                    Clear selection
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(data.signal_responses).map(([key, text]) => (
                  <SignalCard
                    key={key}
                    signalKey={key}
                    text={text}
                    count={data.signal_counts?.[key] ?? 0}
                    isActive={activeSignal === key}
                    onDismiss={() => setActiveSignal(null)}
                  />
                ))}
              </div>
            </div>

            <SummaryPanel summary={data.summary} />

            <RunHistory history={history} />
          </>
        )}
      </main>
    </div>
  )
}