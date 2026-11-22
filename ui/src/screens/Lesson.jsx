import { useState, useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'


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

const PINK = '#FF9ED6'
const PINK_RIM = '#F472B6'
const PINK_MAT = { color: PINK, roughness: 0.75, metalness: 0 }

const CLOUD_OFFSETS = [
  [-0.10,  0.08,  0.29],
  [ 0.11,  0.09,  0.27],
  [-0.13, -0.08,  0.27],
  [ 0.09, -0.09,  0.29],
  [-0.01,  0.01,  0.33],
]

// state: 'idle' | 'listening' | 'speaking'
function BlobMesh({ state = 'idle', analyserRef }) {
  const groupRef      = useRef()
  const eyeLRef       = useRef()
  const eyeRRef       = useRef()
  const closedEyeLRef = useRef()
  const closedEyeRRef = useRef()
  const mouthOpenRef  = useRef()
  const smileRef      = useRef()

  // Cute upward arch for closed eyes (^ shape)
  const closedEyeCurve = useMemo(() => new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(-0.065, -0.022, 0),
    new THREE.Vector3(0,  0.048, 0),
    new THREE.Vector3( 0.065, -0.022, 0),
  ), [])

  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    if (!groupRef.current) return

    if (state === 'listening') {
      // Gentle attentive bob
      groupRef.current.position.y = Math.sin(t * 2.8) * 0.03
      groupRef.current.rotation.z = Math.sin(t * 1.8) * 0.014

      // Eyes closed (cute ^ arches)
      if (eyeLRef.current)       eyeLRef.current.visible       = false
      if (eyeRRef.current)       eyeRRef.current.visible       = false
      if (closedEyeLRef.current) closedEyeLRef.current.visible = true
      if (closedEyeRRef.current) closedEyeRRef.current.visible = true

      // Relaxed smile
      if (mouthOpenRef.current) mouthOpenRef.current.visible = false
      if (smileRef.current)     smileRef.current.visible     = true

    } else if (state === 'speaking') {
      // Expressive speaking movement
      groupRef.current.position.y = Math.sin(t * 3.8) * 0.04
      groupRef.current.rotation.z = Math.sin(t * 2.5) * 0.02

      // Eyes open
      if (eyeLRef.current) {
        eyeLRef.current.visible = true
        eyeLRef.current.scale.y = 1
      }
      if (eyeRRef.current) {
        eyeRRef.current.visible = true
        eyeRRef.current.scale.y = 1
      }
      if (closedEyeLRef.current) closedEyeLRef.current.visible = false
      if (closedEyeRRef.current) closedEyeRRef.current.visible = false

      // Audio-driven or fallback sine mouth
      if (mouthOpenRef.current) {
        mouthOpenRef.current.visible = true
        let amp = 0
        if (analyserRef?.current) {
          const buf = new Uint8Array(analyserRef.current.frequencyBinCount)
          analyserRef.current.getByteFrequencyData(buf)
          const low = Array.from(buf.slice(0, 12)).reduce((a, b) => a + b, 0)
          amp = Math.min(1, low / (12 * 160))
        } else {
          amp = Math.abs(Math.sin(t * 8.5)) * 0.68
        }
        mouthOpenRef.current.scale.y = 0.28 + amp * 1.5
        mouthOpenRef.current.scale.x = 1    + amp * 0.18
      }
      if (smileRef.current) smileRef.current.visible = false

    } else {
      // IDLE — gentle float + periodic blink
      groupRef.current.position.y = Math.sin(t * 2) * 0.04
      groupRef.current.rotation.z = Math.sin(t * 1.2) * 0.02

      const phase  = (t % 4.0) / 4.0
      const blink  = phase > 0.88 && phase < 0.95 ? 0.07 : 1

      if (eyeLRef.current) {
        eyeLRef.current.visible = true
        eyeLRef.current.scale.y = blink
      }
      if (eyeRRef.current) {
        eyeRRef.current.visible = true
        eyeRRef.current.scale.y = blink
      }
      if (closedEyeLRef.current) closedEyeLRef.current.visible = false
      if (closedEyeRRef.current) closedEyeRRef.current.visible = false

      if (mouthOpenRef.current) mouthOpenRef.current.visible = false
      if (smileRef.current)     smileRef.current.visible     = true
    }
  })

  return (
    <group ref={groupRef}>

      {/* ── Main body ── */}
      <mesh>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial {...PINK_MAT} />
      </mesh>

      {/* ── Face window border (medium pink rim) ── */}
      <mesh position={[0, -0.05, 0.86]} scale={[0.70, 0.64, 0.15]}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial color={PINK_RIM} roughness={0.85} metalness={0} />
      </mesh>

      {/* ── Face window (white) ── */}
      <mesh position={[0, -0.05, 0.878]} scale={[0.67, 0.61, 0.12]}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial color="#FFFFFF" roughness={0.9} metalness={0} />
      </mesh>

      {/* ── Green head ornament ── */}
      <group position={[0.76, 0.86, 0.26]}>
        <mesh>
          <sphereGeometry args={[0.33, 32, 32]} />
          <meshStandardMaterial color="#4ADE80" roughness={0.9} metalness={0} />
        </mesh>
        {CLOUD_OFFSETS.map((pos, i) => (
          <mesh key={i} position={pos}>
            <sphereGeometry args={[0.088, 10, 10]} />
            <meshStandardMaterial color="#86EFAC" roughness={0.9} metalness={0} transparent opacity={0.78} />
          </mesh>
        ))}
      </group>

      {/* ── Open eyes — idle + speaking ── */}
      <group ref={eyeLRef} position={[-0.19, 0.08, 0.975]}>
        <mesh scale={[1, 1.28, 0.68]}>
          <sphereGeometry args={[0.095, 24, 24]} />
          <meshStandardMaterial color="#1a1a2e" roughness={0.5} metalness={0.05} />
        </mesh>
      </group>
      <group ref={eyeRRef} position={[0.19, 0.08, 0.975]}>
        <mesh scale={[1, 1.28, 0.68]}>
          <sphereGeometry args={[0.095, 24, 24]} />
          <meshStandardMaterial color="#1a1a2e" roughness={0.5} metalness={0.05} />
        </mesh>
      </group>

      {/* ── Closed eyes — listening (cute ^ arch) ── */}
      <mesh ref={closedEyeLRef} position={[-0.19, 0.08, 0.978]} visible={false}>
        <tubeGeometry args={[closedEyeCurve, 12, 0.025, 6, false]} />
        <meshStandardMaterial color="#1a1a2e" roughness={0.5} />
      </mesh>
      <mesh ref={closedEyeRRef} position={[0.19, 0.08, 0.978]} visible={false}>
        <tubeGeometry args={[closedEyeCurve, 12, 0.025, 6, false]} />
        <meshStandardMaterial color="#1a1a2e" roughness={0.5} />
      </mesh>

      
      {/* ── Idle/listening mouth — small parted smile (like reference) ── */}
      <group ref={smileRef} position={[0, -0.265, 0.968]}>
        <mesh scale={[1.55, 1.0, 0.52]}>
          <sphereGeometry args={[0.088, 20, 20]} />
          <meshStandardMaterial color="#E11D48" roughness={0.8} />
        </mesh>
      </group>

      {/* ── Speaking mouth (open, amplitude-driven) ── */}
      <group ref={mouthOpenRef} position={[0, -0.27, 0.965]} visible={false}>
        <mesh scale={[1.3, 1, 0.55]}>
          <sphereGeometry args={[0.125, 16, 16]} />
          <meshStandardMaterial color="#E11D48" roughness={0.8} />
        </mesh>
      </group>

      {/* ── Left arm ── */}
      <group position={[-1.12, 0.22, 0.1]} rotation={[0.0, -0.2, 0.52]}>
        <mesh>
          <capsuleGeometry args={[0.155, 0.42, 8, 16]} />
          <meshStandardMaterial {...PINK_MAT} />
        </mesh>
        <mesh position={[0, 0.34, 0]}>
          <sphereGeometry args={[0.195, 16, 16]} />
          <meshStandardMaterial {...PINK_MAT} />
        </mesh>
      </group>

      {/* ── Right arm ── */}
      <group position={[1.12, 0.08, 0.1]} rotation={[0.0, 0.2, -0.42]}>
        <mesh>
          <capsuleGeometry args={[0.155, 0.42, 8, 16]} />
          <meshStandardMaterial {...PINK_MAT} />
        </mesh>
        <mesh position={[0, 0.34, 0]}>
          <sphereGeometry args={[0.195, 16, 16]} />
          <meshStandardMaterial {...PINK_MAT} />
        </mesh>
      </group>

      {/* ── Feet ── */}
      <mesh position={[-0.31, -1.1, 0.1]} scale={[1.1, 0.72, 1.1]}>
        <sphereGeometry args={[0.235, 20, 20]} />
        <meshStandardMaterial {...PINK_MAT} />
      </mesh>
      <mesh position={[0.31, -1.1, 0.1]} scale={[1.1, 0.72, 1.1]}>
        <sphereGeometry args={[0.235, 20, 20]} />
        <meshStandardMaterial {...PINK_MAT} />
      </mesh>

    </group>
  )
}

function BlobCharacter({ state = 'idle', bubble, analyserRef }) {
  return (
    <div className="blob-char-wrap">
      {bubble && (
        <div className="blob-bubble">
          <span>{bubble}</span>
        </div>
      )}
      <div className="blob-char-3d">
        <Canvas
          camera={{ position: [0, 0, 4.2], fov: 50 }}
          gl={{ antialias: true, alpha: true }}
          style={{ background: 'transparent' }}
        >
          <ambientLight intensity={1.8} />
          <directionalLight position={[3, 5, 5]}   intensity={0.75} />
          <directionalLight position={[-3, 3, 4]}  intensity={0.55} />
          <BlobMesh state={state} analyserRef={analyserRef} />
        </Canvas>
      </div>
    </div>
  )
}

// Connects an <audio> element to a Web Audio AnalyserNode for real lip sync.
// Call this once when the AI starts playing TTS audio.
function createAnalyserFromAudio(audioEl, analyserRef) {
  if (analyserRef.current) return
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const src = ctx.createMediaElementSource(audioEl)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 512
    analyser.smoothingTimeConstant = 0.8
    src.connect(analyser)
    analyser.connect(ctx.destination)
    analyserRef.current = analyser
  } catch (e) {
    // ignore if already connected or browser restriction
  }
}

// Convert any browser-recorded audio blob to 16 kHz mono WAV PCM
// (soundfile on the backend only reads WAV/FLAC/OGG, not webm/opus)
async function blobToWav(blob) {
  const arrayBuffer = await blob.arrayBuffer()
  const tmpCtx = new AudioContext()
  const decoded = await tmpCtx.decodeAudioData(arrayBuffer)
  tmpCtx.close()

  const targetRate = 16000
  const length = Math.ceil(decoded.duration * targetRate)
  const offCtx = new OfflineAudioContext(1, length, targetRate)
  const src = offCtx.createBufferSource()
  src.buffer = decoded
  src.connect(offCtx.destination)
  src.start(0)
  const rendered = await offCtx.startRendering()

  const pcm = rendered.getChannelData(0)
  const wav = new ArrayBuffer(44 + pcm.length * 2)
  const v = new DataView(wav)
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)) }
  w(0, 'RIFF'); v.setUint32(4, 36 + pcm.length * 2, true)
  w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true)
  v.setUint16(20, 1, true); v.setUint16(22, 1, true)
  v.setUint32(24, 16000, true); v.setUint32(28, 32000, true)
  v.setUint16(32, 2, true); v.setUint16(34, 16, true)
  w(36, 'data'); v.setUint32(40, pcm.length * 2, true)
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]))
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
  }
  return new Blob([wav], { type: 'audio/wav' })
}

const THINKING_PHRASES = [
  { es: '💡 "el agua" es femenino pero usa "el"', en: '"el agua" (water) is feminine but takes the masculine article — a quirk of Spanish!' },
  { es: '💡 "ser" es permanente, "estar" es temporal', en: '"ser" = permanent traits (I am tall); "estar" = temporary states (I am tired)' },
  { es: '💡 En español, los adjetivos van después del sustantivo', en: 'Adjectives usually come after the noun: "casa roja" (red house), not "roja casa"' },
  { es: '💡 "tú" es informal, "usted" es formal', en: '"tú" = you (friends/family); "usted" = you (formal/respectful)' },
  { es: '💡 Los días de la semana no se escriben con mayúscula', en: 'Days of the week are lowercase in Spanish: lunes, martes, miércoles…' },
  { es: '💡 "hay" significa "there is" y "there are"', en: '"hay" covers both singular and plural: "hay un gato" / "hay dos gatos"' },
  { es: '💡 Los números del 1 al 10: uno, dos, tres, cuatro, cinco…', en: 'Numbers 1–10: one, two, three, four, five, six, seven, eight, nine, ten' },
]

export default function Lesson({ onQuiz }) {
  const [topic, setTopic] = useState('')
  const [pdf, setPdf] = useState(null)
  const [chapter, setChapter] = useState('')
  const [chapterId, setChapterId] = useState(null)
  const [chapters, setChapters] = useState([])
  const [lessonActive, setLessonActive] = useState(false)
  const [captionOn, setCaptionOn] = useState(false)
  const [showPopover, setShowPopover] = useState(false)
  const [charState, setCharState] = useState('idle')
  const [bubbleText, setBubbleText] = useState(null)
  const [bubbleEn, setBubbleEn] = useState(null)
  const [isThinking, setIsThinking] = useState(false)
  const [thinkingFact, setThinkingFact] = useState(THINKING_PHRASES[0])
  const [errorMsg, setErrorMsg] = useState(null)
  const [lastSession, setLastSession] = useState(null)  // { id, source_ref, level, step }

  const analyserRef      = useRef(null)
  const audioRef         = useRef(null)
  const fileRef          = useRef()
  const mediaRecorderRef = useRef(null)
  const audioChunksRef   = useRef([])
  const silenceTimerRef  = useRef(null)
  const charStateRef     = useRef('idle')
  const sessionIdRef     = useRef(null)
  const audioPlayingRef  = useRef(false)  // true while Hernando's TTS audio is playing
  const openerInFlightRef = useRef(false)  // guard against double opener calls

  charStateRef.current = charState

  // Fetch last session on mount for the resume card
  useEffect(() => {
    fetch('/api/sessions?limit=1')
      .then(r => r.ok ? r.json() : [])
      .then(sessions => { if (sessions.length) setLastSession(sessions[0]) })
      .catch(() => {})
  }, [])

  const progress    = 0
  const canStart    = topic.trim() || chapter
  const bookName    = pdf?.name ? pdf.name.replace(/\.pdf$/i, '') : null
  const pageTitle   = bookName ?? (topic.trim() || null)
  const chapterName = chapter || null

  const welcomeCaption = pageTitle
    ? `¡Hola! Today we're learning "${pageTitle}"${chapterName ? ` — ${chapterName}` : ''}. Let's get started!`
    : '¡Hola! Select a topic or upload a PDF, then click the mic to begin.'

  // ── Session ──────────────────────────────────────────────────────────────

  async function handleStartLesson() {
    if (openerInFlightRef.current) return
    openerInFlightRef.current = true
    setLessonActive(true)
    setCharState('idle')
    setErrorMsg(null)

    try {
      const body = {
        source_type: chapterId ? 'chapter' : 'topic',
        source_ref: chapter || topic.trim() || 'conversation',
        level: 'A1',
        ...(chapterId ? { chapter_id: chapterId } : {}),
      }
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const data = await res.json()
        sessionIdRef.current = data.session_id
        setTopic('')
        console.log('[session] created — id', data.session_id)

        // Ask Hernando to open the lesson
        console.log('[opener] requesting opening line …')
        try {
          const openerRes = await fetch(`/api/sessions/${data.session_id}/opener`, { method: 'POST' })
          if (openerRes.ok) {
            const opener = await openerRes.json()
            console.log('[opener] received — es:', opener.tutor_message?.es)
            if (opener.tutor_message?.es) setBubbleText(opener.tutor_message.es)
            if (opener.tutor_message?.en) setBubbleEn(opener.tutor_message.en)
            if (opener.audio_b64 && audioRef.current) {
              const bytes = Uint8Array.from(atob(opener.audio_b64), c => c.charCodeAt(0))
              const isWav = bytes[0] === 82 && bytes[1] === 73 && bytes[2] === 70 && bytes[3] === 70
              if (isWav) {
                const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
                audioRef.current.src = url
                audioRef.current.play().catch(() => { console.warn('[opener] autoplay blocked'); setCharState('idle') })
              } else {
                console.warn('[opener] audio not WAV (fake mode?) — skipping playback')
                setCharState('idle')
              }
            } else {
              console.warn('[opener] no audio returned')
              setCharState('idle')
            }
          } else {
            console.error('[opener] failed —', await openerRes.text())
            setCharState('idle')
          }
        } catch (err) {
          console.error('[opener] error —', err)
          setCharState('idle')
        }
      } else {
        const detail = await res.text()
        setErrorMsg(`Could not start session: ${detail}`)
        setLessonActive(false)
      }
    } catch (err) {
      setErrorMsg('Could not reach the server. Is the backend running?')
      setLessonActive(false)
    } finally {
      openerInFlightRef.current = false
    }
  }

  async function handleResume() {
    if (openerInFlightRef.current) return
    openerInFlightRef.current = true
    if (!lastSession) return
    setLessonActive(true)
    setCharState('idle')
    setErrorMsg(null)
    sessionIdRef.current = lastSession.id
    console.log('[resume] session id', lastSession.id)
    try {
      const openerRes = await fetch(`/api/sessions/${lastSession.id}/opener`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ input: 'resume' }) })
      if (openerRes.ok) {
        const opener = await openerRes.json()
        if (opener.tutor_message?.es) setBubbleText(opener.tutor_message.es)
        if (opener.tutor_message?.en) setBubbleEn(opener.tutor_message.en)
        if (opener.audio_b64 && audioRef.current) {
          const bytes = Uint8Array.from(atob(opener.audio_b64), c => c.charCodeAt(0))
          if (bytes[0] === 82 && bytes[1] === 73) {
            audioRef.current.src = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
            audioRef.current.play().catch(() => setCharState('idle'))
          } else { setCharState('idle') }
        } else { setCharState('idle') }
      } else { setCharState('idle') }
    } catch (err) {
      console.error('[resume] error', err)
      setCharState('idle')
    } finally {
      openerInFlightRef.current = false
    }
  }

  function handleEndLesson() {
    stopRecording()
    setShowPopover(true)
    setCharState('idle')
    setBubbleText(null)
  }

  // ── PDF upload ────────────────────────────────────────────────────────────

  async function handlePdfUpload(file) {
    setPdf(file)
    setChapter('')
    setChapterId(null)
    setChapters([])

    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch('/api/books', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(await res.text())
      const { book_id } = await res.json()
      const chapRes = await fetch(`/api/books/${book_id}/chapters`)
      if (chapRes.ok) setChapters(await chapRes.json())
    } catch (err) {
      console.error('PDF upload failed:', err)
    }
  }

  // ── Mic button ────────────────────────────────────────────────────────────

  async function handleMicClick() {
    if (charStateRef.current === 'listening') {
      stopRecording()
      return
    }
    if (charStateRef.current === 'speaking') return
    if (audioPlayingRef.current) return  // block mic while Hernando's audio is playing

    if (!sessionIdRef.current) {
      await handleStartLesson()
    }
    startListening()
  }

  // ── Recording with silence detection ─────────────────────────────────────

  function startListening() {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const ctx = new (window.AudioContext || window.webkitAudioContext)()
        const src = ctx.createMediaStreamSource(stream)
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 512
        src.connect(analyser)

        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm'

        const recorder = new MediaRecorder(stream, { mimeType })
        audioChunksRef.current = []
        recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
        recorder.onstop = () => {
          stream.getTracks().forEach(t => t.stop())
          const blob = new Blob(audioChunksRef.current, { type: mimeType })
          sendVoiceToBackend(blob)
        }
        recorder.start(100)
        mediaRecorderRef.current = recorder
        setCharState('listening')

        // Silence detection — only kicks in after 2s minimum, stops after 1.5s of quiet
        const buf = new Uint8Array(analyser.frequencyBinCount)
        let silenceStart = null
        const recordingStart = Date.now()
        const checkSilence = () => {
          if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') return
          analyser.getByteTimeDomainData(buf)
          const rms = Math.sqrt(buf.reduce((s, v) => s + (v - 128) ** 2, 0) / buf.length)
          const elapsed = Date.now() - recordingStart
          if (rms < 5 && elapsed > 2000) {
            if (!silenceStart) silenceStart = Date.now()
            else if (Date.now() - silenceStart > 1500) { stopRecording(); return }
          } else {
            silenceStart = null
          }
          silenceTimerRef.current = setTimeout(checkSilence, 100)
        }
        silenceTimerRef.current = setTimeout(checkSilence, 400)
      })
      .catch(err => {
        console.error('Microphone access denied:', err)
        setCharState('idle')
      })
  }

  function stopRecording() {
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
    } else if (charStateRef.current === 'listening') {
      setCharState('idle')
    }
  }

  // ── Voice turn ─────────────────────────────────────────────────────────

  async function sendVoiceToBackend(blob) {
    const sid = sessionIdRef.current
    if (!sid) { console.error('[voice] no session id — aborting'); setCharState('idle'); return }

    console.log('[voice] converting blob to WAV …')
    setIsThinking(true)
    setThinkingFact(THINKING_PHRASES[Math.floor(Math.random() * THINKING_PHRASES.length)])
    // Hernando's last bubble stays visible while we wait — thinking fact shows as subtitle

    let wavBlob
    try {
      wavBlob = await blobToWav(blob)
      console.log('[voice] WAV ready —', wavBlob.size, 'bytes')
    } catch (err) {
      console.error('[voice] WAV conversion failed:', err)
      setCharState('idle')
      return
    }

    const formData = new FormData()
    formData.append('audio', wavBlob, 'recording.wav')

    console.log('[voice] sending to backend …')
    try {
      const res = await fetch(`/api/sessions/${sid}/turns/voice?level=A1`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) { console.error('[voice] turn failed:', await res.text()); setCharState('idle'); return }
      const data = await res.json()
      console.log('[voice] response — es:', data.tutor_message?.es, '| unclear:', data.tutor_message?.kind)

      setIsThinking(false)
      if (data.tutor_message?.es) setBubbleText(data.tutor_message.es)
      if (data.tutor_message?.en) setBubbleEn(data.tutor_message.en)

      if (data.audio_b64 && audioRef.current) {
        const bytes = Uint8Array.from(atob(data.audio_b64), c => c.charCodeAt(0))
        const isWav = bytes[0] === 82 && bytes[1] === 73 && bytes[2] === 70 && bytes[3] === 70
        if (!isWav) { console.warn('[voice] audio not WAV — skipping playback'); setCharState('idle'); return }
        console.log('[voice] playing audio —', bytes.length, 'bytes')
        const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
        audioRef.current.src = url
        audioRef.current.play().catch(e => { console.warn('[voice] autoplay blocked:', e); setCharState('idle') })
      } else {
        console.warn('[voice] no audio in response')
        setCharState('idle')
      }
    } catch (err) {
      console.error('[voice] turn error:', err)
      setIsThinking(false)
      setCharState('idle')
    }
  }

  function handleAudioPlay(e) {
    createAnalyserFromAudio(e.target, analyserRef)
    audioPlayingRef.current = true
    setCharState('speaking')
  }

  function handleAudioEnded(e) {
    if (e.target.src?.startsWith('blob:')) URL.revokeObjectURL(e.target.src)
    setCharState('idle')
    // Keep mic blocked for 800ms after audio ends so residual speaker sound
    // doesn't get picked up when the user taps mic immediately after
    setTimeout(() => { audioPlayingRef.current = false }, 800)
  }

  const statusLabel = {
    idle:      'Ready when you are...',
    listening: 'Listening...',
    speaking:  'Assistant is speaking...',
  }[charState]

  return (
    <div className="lesson-fullscreen">
      <audio ref={audioRef} style={{ display: 'none' }}
        onPlay={handleAudioPlay}
        onEnded={handleAudioEnded}
        onError={() => setCharState('idle')}
      />

      {/* Left: robot stage */}
      <div className="lesson-stage">
        <div className="char-glow" />
        <BlobCharacter
          state={charState}
          bubble={bubbleText || welcomeCaption}
          analyserRef={analyserRef}
        />

        {/* Mic button — always visible */}
        <button
          className={`mic-btn ${charState === 'listening' ? 'mic-btn--active' : ''}`}
          onClick={handleMicClick}
          disabled={charState === 'speaking'}
          title={charState === 'listening' ? 'Click to stop' : 'Click to speak'}
        >
          {charState === 'listening' ? '🎙' : '🎤'}
        </button>

        <div className="speaking-status">
          <div className="dot-row">
            <div className={`s-dot ${charState !== 'idle' ? 's-dot--active' : ''}`} />
            <div className={`s-dot ${charState === 'speaking' ? 's-dot--active' : ''}`} />
            <div className={`s-dot ${charState === 'speaking' ? 's-dot--active' : ''}`} />
          </div>
          {charState !== 'speaking' && (
            <div className="speaking-label">{statusLabel}</div>
          )}
        </div>
        {lessonActive && <ProgressRing pct={progress} />}
      </div>

      {/* Right: info + controls panel */}
      <div className="lesson-info-panel">
        <div className="panel-badge">🇪🇸 Tu tutor de español</div>
        <div className="panel-heading">¿Qué quieres aprender?</div>
        <div className="panel-sub">Pick up where you left off or start something new</div>

        {errorMsg && (
          <div className="error-banner" style={{ color: '#dc2626', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: 14 }}>
            {errorMsg}
          </div>
        )}

        <div
          className="resume-card-sm"
          onClick={lastSession ? handleResume : undefined}
          style={lastSession ? { cursor: 'pointer' } : { opacity: 0.5 }}
        >
          <div className="resume-icon-sm">▶</div>
          <div>
            <div className="resume-title-sm">Resume</div>
            <div className="resume-sub-sm">
              {lastSession ? lastSession.display_name : 'No previous session yet'}
            </div>
          </div>
        </div>

        <div className="panel-divider" />

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
            onChange={e => { const f = e.target.files[0]; if (f) handlePdfUpload(f) }} />

          {pdf && (
            <div className="pdf-chip">
              <span>📄 {pdf.name}</span>
              <button onClick={() => { setPdf(null); setChapter(''); setChapterId(null); setChapters([]) }}>✕</button>
            </div>
          )}
          {chapters.length > 0 && (
            <select className="chapter-select"
              value={chapterId ? String(chapterId) : ''}
              onChange={e => {
                const sel = chapters.find(c => String(c.id) === e.target.value)
                if (sel) { setChapter(sel.title); setChapterId(sel.id) }
                else { setChapter(''); setChapterId(null) }
              }}>
              <option value="">Select a chapter…</option>
              {chapters.map(c => <option key={c.id} value={String(c.id)}>{c.title}</option>)}
            </select>
          )}
        </div>

        <div className="caption-toggle-row" style={{ marginBottom: 10 }}>
          <span className="caption-toggle-label">🌐 Translation (EN)</span>
          <button
            className={`toggle-pill ${captionOn ? 'on' : ''}`}
            onClick={() => setCaptionOn(v => !v)}
          />
        </div>
        {captionOn && (
          <div className="caption-box" style={{ marginBottom: 16 }}>
            {isThinking
              ? '…'
              : bubbleEn || (lessonActive ? null : 'Select a topic or upload a PDF, then click Start Lesson.')}
          </div>
        )}

        {lessonActive ? (
          <button className="btn-primary"
            style={{ flex: 'none', width: 'fit-content', padding: '11px 22px' }}
            onClick={handleEndLesson}>
            End lesson
          </button>
        ) : (
          <button className="btn-primary"
            style={{ flex: 'none', width: 'fit-content', padding: '11px 22px', alignSelf: 'center' }}
            disabled={!canStart}
            onClick={handleStartLesson}>
            Start Lesson →
          </button>
        )}
      </div>

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
              <button className="popover-btn-primary" onClick={() => onQuiz(pageTitle || topic || 'Quiz', chapterId, sessionIdRef.current)}>Start Quiz →</button>
              <button className="popover-btn-ghost" onClick={() => setShowPopover(false)}>Revisit lesson</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
