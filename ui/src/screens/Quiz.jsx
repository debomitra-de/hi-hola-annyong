import { useState } from 'react'

const QUESTIONS = [
  {
    type: 'Vocabulary', typeIcon: '📚',
    q: 'What does "la manzana" mean in English?',
    hint: 'Think of a common fruit',
    choices: ['The orange', 'The apple', 'The banana', 'The grape'],
    answer: 1,
  },
  {
    type: 'Comprehension', typeIcon: '💬',
    q: '¿Qué quieres beber? She is asking you what?',
    hint: 'Focus on "beber"',
    choices: ['What you want to eat', 'What you want to drink', 'Where you want to go', 'How you are feeling'],
    answer: 1,
  },
  {
    type: 'Fill in the blank', typeIcon: '✏️',
    q: 'Complete: "Quiero ___ café, por favor."',
    hint: 'The word means "one" (masculine)',
    isFill: true, answer: 'un',
  },
  {
    type: 'Vocabulary', typeIcon: '📚',
    q: 'How do you say "the restaurant" in Spanish?',
    hint: 'It sounds very similar to the English word',
    choices: ['La cocina', 'El restaurante', 'La tienda', 'El mercado'],
    answer: 1,
  },
  {
    type: 'Comprehension', typeIcon: '💬',
    q: '"La cuenta, por favor" — what are you asking for?',
    hint: 'Common phrase at the end of a meal',
    choices: ['The menu', 'More water', 'The bill', 'A dessert'],
    answer: 2,
  },
]

const NEW_WORDS  = ['la manzana', 'beber', 'el restaurante', 'la cuenta', 'quiero']
const REVIEW_ITEMS = ['Numbers 11–20', 'Ser vs. Estar']

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

export default function Quiz({ onHome, topic }) {
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState(null)
  const [fillVal, setFillVal] = useState('')
  const [answered, setAnswered] = useState(false)
  const [results, setResults] = useState([])
  const [done, setDone] = useState(false)

  const q = QUESTIONS[current]
  const isCorrect = q.isFill
    ? fillVal.trim().toLowerCase() === q.answer
    : selected === q.answer

  function handleChoice(i) {
    if (answered) return
    setSelected(i)
    setAnswered(true)
  }

  function handleNext() {
    const next = [...results, isCorrect]
    if (current + 1 >= QUESTIONS.length) {
      setResults(next); setDone(true)
    } else {
      setResults(next); setCurrent(c => c + 1)
      setSelected(null); setFillVal(''); setAnswered(false)
    }
  }

  const score = results.filter(Boolean).length

  if (done) {
    const pct = Math.round((score / QUESTIONS.length) * 100)
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
            <div className="results-sub">{pct}% accuracy · {score}/{QUESTIONS.length} correct</div>
          </div>
          <div className="score-tiles">
            <div className="score-tile"><div className="val">{score}</div><div className="lbl">Correct</div></div>
            <div className="score-tile"><div className="val">{QUESTIONS.length - score}</div><div className="lbl">Missed</div></div>
            <div className="score-tile"><div className="val">{pct}%</div><div className="lbl">Score</div></div>
          </div>
          <div className="words-section">
            <div className="words-label">New words learned</div>
            <div className="word-chips">{NEW_WORDS.map(w => <span key={w} className="chip">{w}</span>)}</div>
          </div>
          {REVIEW_ITEMS.length > 0 && (
            <div className="words-section">
              <div className="words-label">Needs more practice</div>
              <div className="word-chips">{REVIEW_ITEMS.map(w => <span key={w} className="chip review">{w}</span>)}</div>
            </div>
          )}
          <div className="results-actions">
            <button className="btn-primary" onClick={onHome}>Next chapter →</button>
            <button className="btn-ghost" onClick={onHome}>Back to home</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="quiz-screen">
      <QuizSidebar
        topic={topic}
        current={current}
        results={results}
        total={QUESTIONS.length}
        onHome={onHome}
      />

      <div className="quiz-content">
        <div className="question-card">
          <div className="q-type-badge"><span>{q.typeIcon}</span><span>{q.type}</span></div>
          <div className="q-text">{q.q}</div>
          {q.hint && <div className="q-hint">Hint: {q.hint}</div>}

          {q.isFill ? (
            <>
              <input
                className="fill-input"
                placeholder="Type your answer…"
                value={fillVal}
                onChange={e => setFillVal(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !answered && setAnswered(true)}
                disabled={answered}
              />
              {!answered && (
                <button className="btn-primary" style={{ maxWidth: 200, marginBottom: 12 }} onClick={() => setAnswered(true)}>
                  Check answer
                </button>
              )}
            </>
          ) : (
            <div className="choice-list">
              {q.choices.map((c, i) => {
                let cls = ''
                if (answered) {
                  if (i === q.answer)              cls = 'correct'
                  else if (i === selected)         cls = 'wrong'
                }
                return (
                  <button key={i} className={`choice ${cls}`} onClick={() => handleChoice(i)} disabled={answered}>
                    <span>{c}</span>
                    {answered && i === q.answer               && <span className="choice-check">✓</span>}
                    {answered && i === selected && i !== q.answer && <span className="choice-check">✗</span>}
                  </button>
                )
              })}
            </div>
          )}

          {answered && (
            <div className={`answer-feedback ${isCorrect ? 'correct' : 'wrong'}`}>
              {isCorrect
                ? '✅ Correct! Well done.'
                : `❌ The correct answer is: "${q.isFill ? q.answer : q.choices[q.answer]}"`}
            </div>
          )}
        </div>

        {answered && (
          <div className="quiz-footer-row">
            <button className="btn-primary" onClick={handleNext}>
              {current + 1 < QUESTIONS.length ? 'Next question →' : 'See results →'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
