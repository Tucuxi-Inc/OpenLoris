export default function MoltenLorisPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <img
        src="/loris-images/Molten_Loris.png"
        alt="MoltenLoris"
        className="h-64 w-auto mb-8"
      />

      <h1 className="text-4xl font-serif text-ink-primary mb-4">
        MoltenLoris
      </h1>

      <p className="font-mono text-sm text-status-warning tracking-wide uppercase mb-6">
        Coming Soon
      </p>

      <div className="max-w-md">
        <p className="font-serif text-ink-secondary leading-relaxed mb-4">
          An autonomous Slack-monitoring agent powered by your organization's knowledge base.
          MoltenLoris will watch your channels and proactively answer questions before anyone
          has to ask.
        </p>

        <p className="font-serif text-ink-tertiary text-sm">
          Stay tuned for updates.
        </p>
      </div>

      <div className="mt-12 border-t border-rule-light pt-8 max-w-sm">
        <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
          Planned Features
        </h3>
        <ul className="space-y-2 text-left">
          <li className="flex gap-2 font-serif text-sm text-ink-secondary">
            <span className="text-ink-muted">-</span>
            Slack channel monitoring
          </li>
          <li className="flex gap-2 font-serif text-sm text-ink-secondary">
            <span className="text-ink-muted">-</span>
            Proactive question detection
          </li>
          <li className="flex gap-2 font-serif text-sm text-ink-secondary">
            <span className="text-ink-muted">-</span>
            Knowledge base integration
          </li>
          <li className="flex gap-2 font-serif text-sm text-ink-secondary">
            <span className="text-ink-muted">-</span>
            Expert escalation when uncertain
          </li>
          <li className="flex gap-2 font-serif text-sm text-ink-secondary">
            <span className="text-ink-muted">-</span>
            Usage analytics and insights
          </li>
        </ul>
      </div>
    </div>
  )
}
