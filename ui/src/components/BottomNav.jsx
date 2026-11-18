const TABS = [
  { id: 'home',   icon: '🏠', label: 'Home'   },
  { id: 'lesson', icon: '🎤', label: 'Lesson' },
  { id: 'quiz',   icon: '📝', label: 'Quiz'   },
]

export default function BottomNav({ active, onNav }) {
  return (
    <nav className="bottom-nav">
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
    </nav>
  )
}
