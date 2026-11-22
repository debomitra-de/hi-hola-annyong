import { useState } from 'react'
import Lesson from './screens/Lesson'
import Quiz from './screens/Quiz'

export default function App() {
  const [screen, setScreen] = useState('lesson')
  const [quizTopic, setQuizTopic] = useState('')
  const [quizChapterId, setQuizChapterId] = useState(null)
  const [quizSessionId, setQuizSessionId] = useState(null)

  return (
    <>
      {screen === 'lesson' && (
        <Lesson onQuiz={(topic, chapterId, sessionId) => {
          setQuizTopic(topic)
          setQuizChapterId(chapterId)
          setQuizSessionId(sessionId)
          setScreen('quiz')
        }} />
      )}
      {screen === 'quiz' && (
        <Quiz topic={quizTopic} chapterId={quizChapterId} sessionId={quizSessionId} onHome={() => setScreen('lesson')} />
      )}
    </>
  )
}
