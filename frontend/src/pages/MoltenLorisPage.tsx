import LorisAvatar from '../components/LorisAvatar'

export default function MoltenLorisPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <LorisAvatar mood="molten" size="2xl" className="mb-8" />

      <h1 className="text-4xl font-serif text-ink-primary mb-4">
        MoltenLoris
      </h1>

      <div className="max-w-md">
        <p className="font-serif text-ink-secondary leading-relaxed mb-4">
          An autonomous Slack-monitoring agent powered by your organization's knowledge base.
          MoltenLoris watches your channels and proactively answers questions before anyone
          has to ask.
        </p>

        <a
          href="https://github.com/Tucuxi-Inc/Loris/blob/main/docs/loris-planning/MOLTENLORIS-SETUP-GUIDE.md"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 border border-ink-accent text-ink-accent font-mono text-sm hover:bg-ink-accent hover:text-bg-primary transition-colors"
        >
          View Setup Guide
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      <div className="mt-12 border-t border-rule-light pt-8 max-w-sm">
        <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
          Key Features
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

      <div className="mt-8 p-4 bg-bg-secondary border border-rule-light max-w-md">
        <p className="font-mono text-xs text-ink-tertiary">
          <strong>Note:</strong> MoltenLoris requires a separate Claude Code instance running
          with Slack access. Configure GDrive sync in Settings to share your knowledge base
          with MoltenLoris.
        </p>
      </div>
    </div>
  )
}
