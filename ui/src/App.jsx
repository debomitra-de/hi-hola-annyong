import { useState } from 'react'
import Lesson from './screens/Lesson'
import Quiz from './screens/Quiz'

export default function App() {
  const [screen, setScreen] = useState('lesson')
  const [quizTopic, setQuizTopic] = useState('')

  return (
    <>
      {screen === 'lesson' && (
        <Lesson onQuiz={(topic) => { setQuizTopic(topic); setScreen('quiz') }} />
      )}
      {screen === 'quiz' && (
        <Quiz topic={quizTopic} onHome={() => setScreen('lesson')} />
      )}
    </>
  )
}
