import { useState, useRef } from 'react'

const SAMPLE_CHAPTERS = ['Chapter 1 – Introduction', 'Chapter 2 – Vocabulary', 'Chapter 3 – Grammar', 'Chapter 4 – Conversation']

export default function Home({ onStart }) {
  const [topic, setTopic] = useState('')
  const [pdf, setPdf] = useState(null)
  const [chapter, setChapter] = useState('')
  const fileRef = useRef()

  const canStart = topic.trim() || chapter

  return (
    <>
      <div className="home-hero">
        <div className="home-hero-greeting">🇪🇸 &nbsp;¡Hola! Welcome back</div>
        <h1 className="home-hero-title">
          Ready to learn<br /><span>Spanish</span> today?
        </h1>
        <p className="home-hero-sub">
          Pick up where you left off or start something new — your tutor is waiting.
        </p>
      </div>

      <div className="home-two-cards">

        {/* Resume — no previous session */}
        <div className="home-card resume-card resume-empty">
          <div className="home-card-icon resume-icon" style={{ opacity: .45 }}>▶</div>
          <div className="home-card-body">
            <div className="home-card-title">Resume</div>
            <div className="home-card-sub">No previous session yet — start a lesson to begin tracking your progress.</div>
          </div>
        </div>

        {/* Start new */}
        <div className="home-card start-card-full">
          <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', marginBottom: 20 }}>
            <div className="home-card-icon start-icon">📖</div>
            <div>
              <div className="home-card-title">Start</div>
              <div className="home-card-sub" style={{ marginBottom: 0 }}>Type a topic or upload a PDF to begin</div>
            </div>
          </div>

          <div className="input-row">
            <input
              className="topic-input"
              placeholder="e.g. Spanish verbs, travel phrases…"
              value={topic}
              onChange={e => setTopic(e.target.value)}
            />
            <button className="plus-btn" onClick={() => fileRef.current.click()} title="Upload PDF">+</button>
          </div>
          <input type="file" accept=".pdf" ref={fileRef} style={{ display: 'none' }}
            onChange={e => { const f = e.target.files[0]; if (f) { setPdf(f); setChapter('') } }} />

          {pdf && (
            <div className="pdf-chip">
              <span>📄 {pdf.name}</span>
              <button onClick={() => { setPdf(null); setChapter('') }}>✕</button>
            </div>
          )}

          {pdf && (
            <select className="chapter-select" value={chapter} onChange={e => setChapter(e.target.value)}>
              <option value="">Select a chapter…</option>
              {SAMPLE_CHAPTERS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          )}

          <button
            className="btn-primary"
            style={{ marginTop: 14, maxWidth: 200 }}
            disabled={!canStart}
            onClick={() => onStart({ topic: topic.trim(), pdf, chapter })}
          >
            Start Lesson →
          </button>
        </div>

      </div>
    </>
  )
}
