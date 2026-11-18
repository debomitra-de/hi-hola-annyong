const TABS = [
  { id: 'home',   icon: '🏠', label: 'Home'   },
  { id: 'lesson', icon: '🎤', label: 'Lesson' },
  { id: 'quiz',   icon: '📝', label: 'Quiz'   },
]

export default function SideNav({ active, onNav }) {
  return (
    <nav className="side-nav">
      <div className="nav-brand">
        <div className="nav-brand-icon">🇪🇸</div>
        <div>
          <div className="nav-brand-title">¡Hola!</div>
          <div className="nav-brand-sub">Spanish Tutor</div>
        </div>
      </div>

      <div className="nav-section-label">Learn</div>
      {TABS.map(t => (
        <button
          key={t.id}
          className={`nav-item ${active === t.id ? 'active' : ''}`}
          onClick={() => onNav(t.id)}
        >
          <span className="nav-icon">{t.icon}</span>
          <span>{t.label}</span>
        </button>
      ))}

      <div className="nav-spacer" />

      <button className="nav-user">
        <div className="nav-avatar">A</div>
        <div>
          <div className="nav-user-name">Alex</div>
          <div className="nav-user-sub">12-day streak 🔥</div>
        </div>
      </button>
    </nav>
  )
}
