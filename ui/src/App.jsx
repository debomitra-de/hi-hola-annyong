import { useState } from 'react'
import Lesson from './screens/Lesson'
import Quiz from './screens/Quiz'

export default function App() {
  const [screen, setScreen] = useState('lesson')

  return (
    <>
      {screen === 'lesson' && <Lesson onQuiz={() => setScreen('quiz')} />}
      {screen === 'quiz'   && <Quiz   onHome={() => setScreen('lesson')} />}
    </>
  )
}
