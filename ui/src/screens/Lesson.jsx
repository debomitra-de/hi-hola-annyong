import { useState, useRef } from 'react'

const SAMPLE_CHAPTERS = [
  'Chapter 1 – Introduction',
  'Chapter 2 – Vocabulary',
  'Chapter 3 – Grammar',
  'Chapter 4 – Conversation',
]

const CIRCUMFERENCE = 2 * Math.PI * 32

function ProgressRing({ pct }) {
  const offset = CIRCUMFERENCE * (1 - pct)
  return (
    <div className="lesson-progress-ring">
      <svg viewBox="0 0 80 80" width="80" height="80">
        <circle className="ring-bg"   cx="40" cy="40" r="32" />
        <circle className="ring-fill" cx="40" cy="40" r="32"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="ring-text">{Math.round(pct * 100)}%</div>
    </div>
  )
}

function Robot() {
  return (
    <div className="robot">
      <div className="robot-head">
        <div className="robot-eye" />
        <div className="robot-eye" />
        <div className="robot-mouth"><div className="robot-mouth-bar" /></div>
      </div>
      <div className="robot-arms">
        <div className="robot-arm" />
        <div className="robot-arm" />
      </div>
      <div className="robot-body">
        <div className="robot-chest">
          {[1,2,3,4,5].map(i => <div key={i} className="chest-bar" />)}
        </div>
      </div>
    </div>
  )
}

export default function Lesson({ onQuiz }) {
  const [topic, setTopic] = useState('')
  const [pdf, setPdf] = useState(null)
  const [chapter, setChapter] = useState('')
  const [lessonActive, setLessonActive] = useState(false)
  const [captionOn, setCaptionOn] = useState(false)
  const [showPopover, setShowPopover] = useState(false)
  const fileRef = useRef()
  const progress = 0

  const canStart = topic.trim() || chapter

  const bookName    = pdf?.name ? pdf.name.replace(/\.pdf$/i, '') : null
  const pageTitle   = bookName ?? (topic.trim() || null)
  const chapterName = chapter || null

  const caption = pageTitle
    ? `Hello! Today we're going to learn about "${pageTitle}"${chapterName ? ` — ${chapterName}` : ''}. I'll walk you through the key vocabulary and important phrases step by step.`
    : "Hello! Select a topic or upload a PDF to begin. I'll guide you through everything step by step."

  return (
    <div className="lesson-fullscreen">
      {/* Left: robot stage */}
      <div className="lesson-stage">
        <div className="char-glow" />
        <Robot />
        <div className="speaking-status">
          <div className="dot-row">
            <div className="s-dot" /><div className="s-dot" /><div className="s-dot" />
          </div>
          <div className="speaking-label">
            {lessonActive ? 'Assistant is speaking…' : 'Ready when you are…'}
          </div>
        </div>
        {lessonActive && <ProgressRing pct={progress} />}
      </div>

      {/* Right: info + controls panel */}
      <div className="lesson-info-panel">
        <div className="panel-badge">🇪🇸 Tu tutor de español</div>
        <div className="panel-heading">¿Qué quieres aprender?</div>
        <div className="panel-sub">Pick up where you left off or start something new</div>

        {/* Resume card */}
        <div className="resume-card-sm">
          <div className="resume-icon-sm">▶</div>
          <div>
            <div className="resume-title-sm">Resume</div>
            <div className="resume-sub-sm">No previous session yet</div>
          </div>
        </div>

        <div className="panel-divider" />

        {/* Topic + PDF */}
        <div className="panel-section">
          <div className="input-row">
            <input
              className="topic-input"
              placeholder="e.g. Spanish verbs, travel phrases…"
              value={topic}
              onChange={e => setTopic(e.target.value)}
            />
            <button className="plus-btn" onClick={() => fileRef.current.click()} title="Upload PDF">📎</button>
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
        </div>

        {/* Translation toggle */}
        <div className="caption-toggle-row" style={{ marginBottom: 10 }}>
          <span className="caption-toggle-label">🌐 Translation (EN)</span>
          <button
            className={`toggle-pill ${captionOn ? 'on' : ''}`}
            onClick={() => setCaptionOn(v => !v)}
          />
        </div>
        {captionOn && <div className="caption-box" style={{ marginBottom: 16 }}>{caption}</div>}

        {/* Action button */}
        {lessonActive ? (
          <button className="btn-primary" onClick={() => setShowPopover(true)}>End lesson</button>
        ) : (
          <button
            className="btn-primary"
            disabled={!canStart}
            onClick={() => setLessonActive(true)}
          >
            Start Lesson →
          </button>
        )}
      </div>

      {/* Completion popover */}
      {showPopover && (
        <div className="popover-overlay">
          <div className="popover-card">
            <div className="popover-emoji">🎉</div>
            <div className="popover-title">Lesson complete!</div>
            <div className="popover-sub">
              Great job finishing <strong>{pageTitle || 'your lesson'}</strong>
              {chapterName ? ` — ${chapterName}` : ''}. Ready to test your knowledge?
            </div>
            <div className="popover-actions">
              <button className="popover-btn-primary" onClick={onQuiz}>Start Quiz →</button>
              <button className="popover-btn-ghost" onClick={() => setShowPopover(false)}>Revisit lesson</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
