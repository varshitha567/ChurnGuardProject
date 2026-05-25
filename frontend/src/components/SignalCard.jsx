import { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SIGNAL_META } from './utils'

const mdComponents = {
  h1: ({ children }) => <h4 className="text-sm font-semibold text-stone-900 mt-3 mb-1.5">{children}</h4>,
  h2: ({ children }) => <h4 className="text-sm font-semibold text-stone-900 mt-3 mb-1.5">{children}</h4>,
  h3: ({ children }) => <h4 className="text-sm font-semibold text-stone-800 mt-3 mb-1">{children}</h4>,
  p:  ({ children }) => <p className="text-xs text-stone-600 leading-relaxed mb-2">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-stone-800">{children}</strong>,
  ul: ({ children }) => <ul className="text-xs text-stone-600 space-y-0.5 pl-4 list-disc mb-2">{children}</ul>,
  ol: ({ children }) => <ol className="text-xs text-stone-600 space-y-0.5 pl-4 list-decimal mb-2">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  hr: () => <hr className="border-stone-100 my-3" />,
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-brand-50">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-stone-100">{children}</tbody>,
  th: ({ children }) => (
    <th className="text-left text-xs font-semibold text-stone-500 uppercase tracking-wide px-3 py-2 border-b border-stone-200">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="px-3 py-1.5 text-stone-600">{children}</td>,
  tr: ({ children }) => <tr className="hover:bg-stone-50">{children}</tr>,
}

export default function SignalCard({ signalKey, text, count, isActive, onDismiss }) {
  const [expanded, setExpanded] = useState(false)
  const ref = useRef(null)
  const meta = SIGNAL_META[signalKey]

  useEffect(() => {
    if (isActive && ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setExpanded(true)
    }
  }, [isActive])

  const preview = text.split('\n').filter(l => l.trim()).slice(0, 2).join(' ').replace(/\*\*/g, '')

  return (
    <div
      ref={ref}
      className={`bg-white rounded-xl border transition-all duration-200 ${
        isActive ? 'border-brand-400 shadow-md shadow-brand-100' : 'border-stone-200'
      }`}
    >
      <button
        className="w-full text-left p-5"
        onClick={() => { setExpanded(!expanded); if (isActive && onDismiss) onDismiss() }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className="w-2.5 h-2.5 rounded-full mt-0.5 flex-shrink-0"
              style={{ backgroundColor: meta.color }}
            />
            <div>
              <h3 className="font-semibold text-stone-900 text-sm">{meta.label}</h3>
              <p className="text-xs text-stone-400 mt-0.5">{meta.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span
              className="text-sm font-bold px-3 py-1 rounded-full"
              style={{ color: meta.color, backgroundColor: meta.bg }}
            >
              {count} customers
            </span>
            <svg
              className={`w-4 h-4 text-stone-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {!expanded && preview && (
          <p className="text-xs text-stone-400 mt-3 ml-5 line-clamp-2">{preview}</p>
        )}
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-stone-100 pt-4 max-h-80 overflow-y-auto scrollbar-thin">
          <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {text}
          </Markdown>
        </div>
      )}
    </div>
  )
}