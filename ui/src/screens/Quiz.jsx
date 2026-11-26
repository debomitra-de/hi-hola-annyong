import { useState, useEffect } from 'react'

function correctOptionText(question) {
  const options = Array.isArray(question.options) ? question.options : []
  const answer = String(question.answer ?? '').trim()
  const exactMatch = options.find(
    option => typeof option === 'string' && option.trim().toLocaleLowerCase() === answer.toLocaleLowerCase(),
  )
  if (exactMatch !== undefined) return exactMatch

  const letterMatch = answer.match(/^(?:option\s*)?([a-d])(?:[.)])?$/i)
  if (letterMatch) {
    const option = options[letterMatch[1].toUpperCase().charCodeAt(0) - 65]
    if (typeof option === 'string') return option
  }
  return answer
}

function QuizSidebar({ topic, current, results, total, onHome }) {
  return (
    <div className="quiz-sidebar">
      <button className="back-btn" onClick={onHome} style={{ alignSelf: 'flex-start' }}>←</button>
      <div className="quiz-sidebar-topic">{topic || 'Quiz'}</div>
      <div className="quiz-sidebar-sub">Question {current + 1} of {total}</div>
      <div className="quiz-nav-list">
        {Array.from({ length: total }, (_, i) => {
          let status = ''
          if (i < results.length) status = results[i] ? 'done' : 'wrong'
          else if (i === current) status = 'curr'
          return (
            <div key={i} className={`quiz-nav-item ${status}`}>
              <span className="quiz-nav-num">
                {i < results.length ? (results[i] ? '✓' : '✗') : i + 1}
              </span>
              <span className="quiz-nav-label">Question {i + 1}</span>
              {i < results.length && (
                <span className="quiz-nav-status">{results[i] ? '✓' : '✗'}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Quiz({ onHome, topic, chapterId, sessionId }) {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading]     = useState(true)
  const [loadErr, setLoadErr]     = useState(null)
  const [current, setCurrent]     = useState(0)
  const [selected, setSelected]   = useState(null)   // index into options[]
  const [answered, setAnswered]   = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [results, setResults]     = useState([])
  const [done, setDone]           = useState(false)

  // Load questions from backend when chapter is available, else show placeholder
  useEffect(() => {
    if (!chapterId && !sessionId) {
      setLoadErr('No session or chapter — go back and finish a lesson first.')
      setLoading(false)
      return
    }

    const url = chapterId
      ? `/api/chapters/${chapterId}/quiz?n_questions=5&level=A1`
      : `/api/sessions/${sessionId}/quiz`

    fetch(url, { method: chapterId ? 'POST' : 'GET' })
      .then(r => {
        if (!r.ok) return r.text().then(t => { throw new Error(t) })
        return r.json()
      })
      .then(qs => {
        if (!qs.length) throw new Error('Backend returned no questions.')
        setQuestions(qs)
        setLoading(false)
      })
      .catch(err => {
        setLoadErr(`Could not load quiz: ${err.message}`)
        setLoading(false)
      })
  }, [chapterId, sessionId])

  function handleCheck() {
    if (answered || selected === null) return
    const q = questions[current]
    const correct = q.options[selected] === correctOptionText(q)
    setIsCorrect(correct)
    setAnswered(true)
  }

  function handleNext() {
    const next = [...results, isCorrect]
    if (current + 1 >= questions.length) {
      setResults(next); setDone(true)
    } else {
      setResults(next); setCurrent(c => c + 1)
      setSelected(null); setAnswered(false); setIsCorrect(false)
    }
  }

  const score = results.filter(Boolean).length

  if (loading) {
    return (
      <div className="quiz-screen" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
          <div>Generating your quiz…</div>
        </div>
      </div>
    )
  }

  if (loadErr) {
    return (
      <div className="quiz-screen" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', maxWidth: 360 }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⚠️</div>
          <div style={{ color: '#dc2626', marginBottom: 16 }}>{loadErr}</div>
          <button className="btn-ghost" onClick={onHome}>← Back</button>
        </div>
      </div>
    )
  }

  if (done) {
    const pct = Math.round((score / questions.length) * 100)
    return (
      <div className="quiz-screen">
        <div className="quiz-sidebar">
          <button className="back-btn" onClick={onHome} style={{ alignSelf: 'flex-start' }}>←</button>
          <div className="quiz-sidebar-topic">{topic || 'Quiz'}</div>
          <div className="quiz-sidebar-sub">Completed</div>
          <div className="quiz-nav-list">
            {results.map((r, i) => (
              <div key={i} className={`quiz-nav-item ${r ? 'done' : 'wrong'}`}>
                <span className="quiz-nav-num">{i + 1}</span>
                <span className="quiz-nav-label">Question {i + 1}</span>
                <span className="quiz-nav-status">{r ? '✓' : '✗'}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="quiz-results">
          <div className="results-top">
            <div className="results-emoji">{pct >= 80 ? '🏆' : pct >= 60 ? '👍' : '💪'}</div>
            <div className="results-title">{pct >= 80 ? 'Excellent!' : pct >= 60 ? 'Good job!' : 'Keep practicing!'}</div>
            <div className="results-sub">{pct}% accuracy · {score}/{questions.length} correct</div>
          </div>
          <div className="score-tiles">
            <div className="score-tile"><div className="val">{score}</div><div className="lbl">Correct</div></div>
            <div className="score-tile"><div className="val">{questions.length - score}</div><div className="lbl">Missed</div></div>
            <div className="score-tile"><div className="val">{pct}%</div><div className="lbl">Score</div></div>
          </div>
          <div className="results-actions">
            <button className="btn-primary" onClick={onHome}>Next chapter →</button>
            <button className="btn-ghost" onClick={onHome}>Back to home</button>
          </div>
        </div>
      </div>
    )
  }

  const q = questions[current]
  const correctAnswer = correctOptionText(q)

  return (
    <div className="quiz-screen">
      <QuizSidebar
        topic={topic}
        current={current}
        results={results}
        total={questions.length}
        onHome={onHome}
      />

      <div className="quiz-content">
        <div className="question-card">
          <div className="q-type-badge"><span>🔤</span><span>Multiple choice</span></div>
          <div className="q-text">{q.question}</div>

          <div className="mcq-options">
            {(q.options || []).map((opt, i) => {
              let cls = 'mcq-option'
              if (answered) {
                if (opt === correctAnswer) cls += ' correct'
                else if (i === selected) cls += ' wrong'
              } else if (i === selected) {
                cls += ' selected'
              }
              return (
                <button
                  key={i}
                  className={cls}
                  onClick={() => !answered && setSelected(i)}
                  disabled={answered}
                >
                  <span className="mcq-letter">{String.fromCharCode(65 + i)}</span>
                  {opt}
                </button>
              )
            })}
          </div>

          {!answered && (
            <button
              className="btn-primary"
              style={{ maxWidth: 200, marginBottom: 12 }}
              onClick={handleCheck}
              disabled={selected === null}
            >
              Check answer
            </button>
          )}

          {answered && (
            <div className={`answer-feedback ${isCorrect ? 'correct' : 'wrong'}`}>
              {isCorrect ? '✅ Correct! Well done.' : `❌ The correct answer is: "${correctAnswer}"`}
            </div>
          )}
        </div>

        {answered && (
          <div className="quiz-footer-row">
            <button className="btn-primary" onClick={handleNext}>
              {current + 1 < questions.length ? 'Next question →' : 'See results →'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
