import { approve } from '../api/client'

const STATUS_CONFIG = {
  idle: {
    label: 'Approve Retention Actions',
    sub: 'Triggers personalised emails and outbound calls for top 10 at-risk customers.',
    btnClass: 'bg-brand-600 hover:bg-brand-700 text-white',
    icon: null,
  },
  loading: {
    label: 'Initiating Actions...',
    sub: 'The action pipeline is running in the background. This takes 2-3 minutes.',
    btnClass: 'bg-brand-400 text-white cursor-not-allowed',
    icon: 'spinner',
  },
  success: {
    label: 'Actions Initiated',
    sub: 'Retention emails and outbound calls have been queued for all priority customers.',
    btnClass: 'bg-emerald-600 text-white cursor-default',
    icon: 'check',
  },
  error: {
    label: 'Action Failed — Retry',
    sub: 'Something went wrong. Check that the backend is running and try again.',
    btnClass: 'bg-red-500 hover:bg-red-600 text-white',
    icon: null,
  },
}

export default function ApprovePanel({ status, onStatusChange }) {
  const cfg = STATUS_CONFIG[status]

  async function handleApprove() {
    if (status !== 'idle' && status !== 'error') return
    onStatusChange('loading')
    try {
      await approve()
      onStatusChange('success')
    } catch {
      onStatusChange('error')
    }
  }

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6 flex flex-col justify-between h-full">
      <div>
        <h2 className="text-base font-semibold text-stone-900">Action Pipeline</h2>
        <p className="text-sm text-stone-400 mt-0.5">
          Send retention actions to the highest-risk customers
        </p>

        <div className="mt-5 space-y-3">
          <div className="flex items-center gap-2.5 text-sm text-stone-600">
            <div className="w-5 h-5 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
              <div className="w-1.5 h-1.5 rounded-full bg-brand-600" />
            </div>
            Personalised retention email per customer
          </div>
          <div className="flex items-center gap-2.5 text-sm text-stone-600">
            <div className="w-5 h-5 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
              <div className="w-1.5 h-1.5 rounded-full bg-brand-600" />
            </div>
            Outbound call initiated with signal context
          </div>
          <div className="flex items-center gap-2.5 text-sm text-stone-600">
            <div className="w-5 h-5 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
              <div className="w-1.5 h-1.5 rounded-full bg-brand-600" />
            </div>
            Top 10 priority customers by signal count
          </div>
        </div>
      </div>

      <div className="mt-6">
        <p className="text-xs text-stone-400 mb-3">{cfg.sub}</p>
        <button
          onClick={handleApprove}
          disabled={status === 'loading' || status === 'success'}
          className={`w-full flex items-center justify-center gap-2.5 py-3.5 px-5 rounded-xl font-semibold text-sm transition-colors ${cfg.btnClass}`}
        >
          {cfg.icon === 'spinner' && (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          )}
          {cfg.icon === 'check' && (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          )}
          {cfg.label}
        </button>
      </div>
    </div>
  )
}