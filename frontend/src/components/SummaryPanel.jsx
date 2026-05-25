import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const mdComponents = {
  h1: ({ children }) => <h3 className="text-base font-semibold text-stone-900 mt-5 mb-2">{children}</h3>,
  h2: ({ children }) => <h3 className="text-base font-semibold text-stone-900 mt-5 mb-2">{children}</h3>,
  h3: ({ children }) => <h4 className="text-sm font-semibold text-stone-800 mt-4 mb-1.5">{children}</h4>,
  p:  ({ children }) => <p className="text-sm text-stone-700 leading-relaxed mb-3">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
  ul: ({ children }) => <ul className="text-sm text-stone-700 space-y-1 pl-5 list-disc mb-3">{children}</ul>,
  ol: ({ children }) => <ol className="text-sm text-stone-700 space-y-1 pl-5 list-decimal mb-3">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  hr: () => <hr className="border-stone-100 my-4" />,
  table: ({ children }) => (
    <div className="overflow-x-auto my-4">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-brand-50">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-stone-100">{children}</tbody>,
  th: ({ children }) => (
    <th className="text-left text-xs font-semibold text-stone-600 uppercase tracking-wide px-4 py-2.5 border-b border-stone-200">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-2.5 text-stone-700 text-sm">{children}</td>
  ),
  tr: ({ children }) => <tr className="hover:bg-stone-50 transition-colors">{children}</tr>,
  code: ({ children }) => (
    <code className="text-xs bg-stone-100 text-stone-700 px-1.5 py-0.5 rounded font-mono">{children}</code>
  ),
}

export default function SummaryPanel({ summary }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="bg-white rounded-xl border border-stone-200">
      <button
        className="w-full flex items-center justify-between px-6 py-5 text-left"
        onClick={() => setOpen(!open)}
      >
        <div>
          <h2 className="text-base font-semibold text-stone-900">Cross-Signal Summary</h2>
          <p className="text-sm text-stone-400 mt-0.5">
            Overlap analysis, priority ranking, and recommended actions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-1 rounded-full">
            AI Generated
          </span>
          <svg
            className={`w-4 h-4 text-stone-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && (
        <div className="px-6 pb-6 border-t border-stone-100 pt-5 max-h-[580px] overflow-y-auto scrollbar-thin">
          <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {summary}
          </Markdown>
        </div>
      )}
    </div>
  )
}