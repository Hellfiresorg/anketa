import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  type ExistingResponse,
  type InvitationData,
  type Question,
  getInvitation,
  submitInvitation,
  submitTextResponse,
} from '../lib/api'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

type Screen =
  | 'loading'
  | 'error'
  | 'not_found'
  | 'gone'
  | 'welcome'
  | 'answering'
  | 'review'
  | 'submitting'
  | 'done'
  | 'readonly'

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */
function getSupportedMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ]
  for (const t of candidates) {
    if (MediaRecorder.isTypeSupported(t)) return t
  }
  return ''
}

function getExtFromMime(mime: string): string {
  if (mime.includes('mp4') || mime.includes('m4a')) return 'm4a'
  if (mime.includes('ogg')) return 'ogg'
  return 'webm'
}

function fmtSec(s: number): string {
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/* ------------------------------------------------------------------ */
/*  Main page                                                           */
/* ------------------------------------------------------------------ */
export default function SurveyPage() {
  const { invitationId } = useParams<{ invitationId: string }>()
  const [screen, setScreen] = useState<Screen>('loading')
  const [data, setData] = useState<InvitationData | null>(null)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentText, setCurrentText] = useState('')
  const [returnToReview, setReturnToReview] = useState(false)
  const [submitError, setSubmitError] = useState('')

  /* ---- localStorage persistence ---- */
  const storageKey = invitationId ? `survey_${invitationId}` : null

  // Save only after data is loaded (guard against overwriting on mount before restore)
  useEffect(() => {
    if (!storageKey || !data) return
    localStorage.setItem(storageKey, JSON.stringify({ answers, currentIdx, currentText }))
  }, [answers, currentIdx, currentText, storageKey, data])

  useEffect(() => {
    if (!invitationId) return
    getInvitation(invitationId)
      .then((d) => {
        setData(d)
        // Restore saved progress if invitation is still in-progress
        if (d.invitation.status !== 'completed' && storageKey) {
          try {
            const raw = localStorage.getItem(storageKey)
            if (raw) {
              const saved = JSON.parse(raw)
              const hasAnswers = saved.answers && Object.keys(saved.answers).length > 0
              const hasText = !!saved.currentText
              if (hasAnswers || hasText) {
                setAnswers(saved.answers || {})
                setCurrentIdx(saved.currentIdx ?? 0)
                setCurrentText(saved.currentText ?? '')
              }
            }
          } catch {}
        }
        setScreen(d.invitation.status === 'completed' ? 'readonly' : 'welcome')
      })
      .catch((e: Error) => {
        if (e.message === 'NOT_FOUND') setScreen('not_found')
        else if (e.message === 'GONE') setScreen('gone')
        else setScreen('error')
      })
  }, [invitationId]) // eslint-disable-line

  const startSurvey = () => {
    // currentText is already set correctly by the restore logic (or is '' for a fresh start)
    // Do NOT override with answers[0] — that was causing wrong text on other questions after refresh
    setScreen('answering')
  }

  const handleNext = (text: string) => {
    if (!data) return
    const q = data.questions[currentIdx]
    const newAnswers = { ...answers, [q.id]: text }
    setAnswers(newAnswers)

    if (returnToReview) {
      setReturnToReview(false)
      setScreen('review')
    } else if (currentIdx + 1 >= data.questions.length) {
      setScreen('review')
    } else {
      const nextIdx = currentIdx + 1
      setCurrentIdx(nextIdx)
      setCurrentText(newAnswers[data.questions[nextIdx].id] ?? '')
    }
  }

  const handleJump = (targetIdx: number) => {
    if (!data) return
    const q = data.questions[currentIdx]
    const newAnswers = q ? { ...answers, [q.id]: currentText } : { ...answers }
    setAnswers(newAnswers)
    setCurrentIdx(targetIdx)
    setCurrentText(newAnswers[data.questions[targetIdx]?.id] ?? '')
  }

  const handleSubmit = async () => {
    if (!invitationId || !data) return
    setSubmitError('')
    setScreen('submitting')
    try {
      for (const q of data.questions) {
        const text = answers[q.id]
        if (text?.trim()) {
          await submitTextResponse(invitationId, q.id, text.trim())
        }
      }
      await submitInvitation(invitationId)
      if (storageKey) localStorage.removeItem(storageKey)
      setScreen('done')
    } catch (e: any) {
      setSubmitError(e?.message || 'Ошибка при отправке.')
      setScreen('review')
    }
  }

  const questions = data?.questions ?? []
  const q = questions[currentIdx]
  const hasSavedProgress = Object.keys(answers).length > 0

  if (screen === 'loading') return <LoadingScreen />
  if (screen === 'not_found') return <ErrorScreen title="Анкета не найдена" body="Проверьте ссылку." />
  if (screen === 'gone') return <ErrorScreen title="Ссылка недействительна" body="Эта анкета больше недоступна." />
  if (screen === 'error') return <ErrorScreen title="Ошибка" body="Не удалось загрузить анкету. Попробуйте позже." />
  if (screen === 'done') return <ThankYouScreen />
  if (screen === 'readonly' && data) return <ReadonlyScreen data={data} />

  if (screen === 'welcome' && data) {
    return (
      <WelcomeScreen
        name={data.invitation.client_name}
        totalQuestions={questions.length}
        hasProgress={hasSavedProgress}
        onStart={startSurvey}
      />
    )
  }

  if (screen === 'answering' && q) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>
        <QuestionNav
          questions={questions}
          currentIdx={currentIdx}
          answers={answers}
          currentText={currentText}
          onJump={handleJump}
        />
        <ProgressBar current={currentIdx + 1} total={questions.length} />
        <div className="client-screen" style={{ paddingTop: 24, flex: 1 }}>
          <QuestionAnswerScreen
            key={q.id}
            q={q}
            currentIdx={currentIdx}
            total={questions.length}
            text={currentText}
            onTextChange={setCurrentText}
            onNext={handleNext}
          />
        </div>
      </div>
    )
  }

  if (screen === 'submitting') {
    return (
      <div className="client-screen" style={{ justifyContent: 'center' }}>
        <p className="client-body-muted pulse">Отправляем анкету...</p>
      </div>
    )
  }

  if (screen === 'review' && data) {
    return (
      <div className="client-screen" style={{ paddingTop: 32 }}>
        <div className="client-review">
          <h2 className="client-h2-brand">Проверьте ответы</h2>
          <p className="client-body-muted">Нажмите на вопрос, чтобы отредактировать ответ.</p>
          {submitError && (
            <p style={{ color: '#ef4444', fontSize: 14, marginTop: 8, marginBottom: 8 }}>
              {submitError}
            </p>
          )}
          <div className="client-review-list">
            {questions.map((question, idx) => (
              <div
                key={question.id}
                className="client-review-item"
                onClick={() => {
                  setReturnToReview(true)
                  setCurrentIdx(idx)
                  setCurrentText(answers[question.id] ?? '')
                  setScreen('answering')
                }}
              >
                <p className="client-review-q">{question.order_index}. {question.text}</p>
                <p className="client-review-a">
                  {answers[question.id] || <span style={{ color: '#d97706' }}>Нет ответа</span>}
                </p>
              </div>
            ))}
          </div>
          <button onClick={handleSubmit} className="client-btn-primary" style={{ marginTop: 32, width: '100%' }}>
            Отправить анкету
          </button>
        </div>
      </div>
    )
  }

  return null
}

/* ------------------------------------------------------------------ */
/*  QuestionNav                                                         */
/* ------------------------------------------------------------------ */
function QuestionNav({
  questions, currentIdx, answers, currentText, onJump,
}: {
  questions: Question[]
  currentIdx: number
  answers: Record<string, string>
  currentText: string
  onJump: (idx: number) => void
}) {
  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center',
      padding: '10px 12px 8px', background: '#fff', borderBottom: '1px solid #f3f4f6',
      position: 'sticky', top: 0, zIndex: 10,
    }}>
      {questions.map((q, idx) => {
        const isCurrent = idx === currentIdx
        const answered = isCurrent ? !!currentText.trim() : !!(answers[q.id]?.trim())
        return (
          <button
            key={q.id}
            onClick={() => onJump(idx)}
            aria-label={`Вопрос ${idx + 1}`}
            aria-current={isCurrent ? 'step' : undefined}
            style={{
              width: 32, height: 32, borderRadius: '50%',
              border: `2px solid ${isCurrent ? '#102f6e' : answered ? '#102f6e' : '#d1d5db'}`,
              background: answered && !isCurrent ? '#102f6e' : isCurrent ? '#e8edf7' : '#fff',
              color: answered && !isCurrent ? '#fff' : isCurrent ? '#102f6e' : '#9ca3af',
              fontWeight: isCurrent ? 700 : 500, fontSize: 13,
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'background 0.15s, border-color 0.15s',
              WebkitTapHighlightColor: 'transparent',
            }}
          >
            {idx + 1}
          </button>
        )
      })}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  ProgressBar                                                         */
/* ------------------------------------------------------------------ */
function ProgressBar({ current, total }: { current: number; total: number }) {
  return (
    <div className="client-progress-track">
      <div className="client-progress-fill" style={{ width: `${(current / total) * 100}%` }} />
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  QuestionAnswerScreen                                                */
/* ------------------------------------------------------------------ */
type RecState = 'idle' | 'recording' | 'transcribing'

function QuestionAnswerScreen({
  q, currentIdx, total, text, onTextChange, onNext,
}: {
  q: Question
  currentIdx: number
  total: number
  text: string
  onTextChange: (t: string) => void
  onNext: (text: string) => void
}) {
  const [recState, setRecState] = useState<RecState>('idle')
  const [recError, setRecError] = useState('')
  const [recSeconds, setRecSeconds] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const textRef = useRef(text)
  useEffect(() => { textRef.current = text }, [text])

  // Stop everything on unmount (e.g. user jumps to different question while recording)
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const micSupported = typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia

  const startRecording = async () => {
    setRecError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunksRef.current = []

      const mimeType = getSupportedMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
        setRecSeconds(0)

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        if (blob.size < 500) { setRecState('idle'); return }

        setRecState('transcribing')
        try {
          const fd = new FormData()
          fd.append('audio', blob, `rec.${getExtFromMime(recorder.mimeType || 'audio/webm')}`)

          const res = await fetch(`${BASE}/api/public/transcribe`, { method: 'POST', body: fd })

          if (res.ok) {
            const data = await res.json()
            if (data.text?.trim()) {
              const prev = textRef.current.trim()
              onTextChange(prev ? prev + ' ' + data.text : data.text)
            }
          } else {
            const err = await res.json().catch(() => ({}))
            setRecError(err.detail || 'Не удалось расшифровать. Попробуйте ещё раз.')
          }
        } catch {
          setRecError('Ошибка связи при расшифровке.')
        } finally {
          setRecState('idle')
        }
      }

      recorder.start()
      setRecState('recording')
      setRecSeconds(0)
      timerRef.current = setInterval(() => setRecSeconds((s) => s + 1), 1000)
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setRecError('Доступ к микрофону запрещён. Разрешите доступ в настройках браузера.')
      } else if (err.name === 'NotFoundError') {
        setRecError('Микрофон не найден.')
      } else {
        setRecError('Не удалось запустить запись.')
      }
    }
  }

  const handleMicClick = () => {
    if (recState === 'transcribing') return
    if (recState === 'recording') {
      mediaRecorderRef.current?.stop()
    } else {
      startRecording()
    }
  }

  return (
    <div className="client-qa">
      <p className="client-caption">Вопрос {q.order_index} из {total}</p>
      <h2 className="client-h2">{q.text}</h2>

      <div className="client-textarea-wrap">
        <textarea
          className="client-textarea"
          placeholder={
            micSupported
              ? 'Введите ответ или нажмите кнопку микрофона для голосового ввода'
              : 'Введите ваш ответ'
          }
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          disabled={recState === 'transcribing'}
        />

        {micSupported && (
          <button
            onClick={handleMicClick}
            disabled={recState === 'transcribing'}
            className={`client-mic-btn${recState === 'recording' ? ' rec' : ''}`}
            title={
              recState === 'recording'
                ? 'Остановить запись'
                : recState === 'transcribing'
                ? 'Расшифровываю...'
                : 'Голосовой ввод'
            }
            aria-label={
              recState === 'recording'
                ? 'Остановить запись'
                : recState === 'transcribing'
                ? 'Расшифровываю'
                : 'Голосовой ввод'
            }
          >
            {recState === 'transcribing' ? (
              /* Spinner */
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            ) : recState === 'recording' ? (
              /* Stop square */
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <rect x="5" y="5" width="14" height="14" rx="2" />
              </svg>
            ) : (
              /* Mic */
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="2" width="6" height="11" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <line x1="12" y1="17" x2="12" y2="22" />
                <line x1="8" y1="22" x2="16" y2="22" />
              </svg>
            )}
          </button>
        )}
      </div>

      {recState === 'recording' && (
        <p style={{ fontSize: 14, color: '#ef4444', marginTop: 8, textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>
          ● Запись {fmtSec(recSeconds)} — нажмите ещё раз, чтобы остановить
        </p>
      )}
      {recState === 'transcribing' && (
        <p style={{ fontSize: 14, color: '#6b7280', marginTop: 8, textAlign: 'center' }}>
          Расшифровываю...
        </p>
      )}
      {recError && (
        <p style={{ fontSize: 14, color: '#d97706', marginTop: 8, textAlign: 'center' }}>
          {recError}
        </p>
      )}

      <button
        onClick={() => onNext(text)}
        disabled={(q.is_required && !text.trim()) || recState !== 'idle'}
        className="client-btn-primary"
        style={{ marginTop: 24, width: '100%' }}
      >
        {currentIdx + 1 < total ? 'Далее →' : 'К проверке'}
      </button>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Status screens                                                      */
/* ------------------------------------------------------------------ */
function LoadingScreen() {
  return (
    <div className="client-screen" style={{ justifyContent: 'center' }}>
      <div className="client-spinner" />
    </div>
  )
}

function ErrorScreen({ title, body }: { title: string; body: string }) {
  return (
    <div className="client-screen" style={{ justifyContent: 'center', textAlign: 'center' }}>
      <h2 className="client-h2">{title}</h2>
      <p className="client-body-muted">{body}</p>
    </div>
  )
}

function WelcomeScreen({
  name, totalQuestions, hasProgress, onStart,
}: {
  name: string
  totalQuestions: number
  hasProgress: boolean
  onStart: () => void
}) {
  return (
    <div className="client-screen" style={{ justifyContent: 'center', padding: '32px 24px' }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        {/* Logo */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 28 }}>
          <div className="client-logo-mark" style={{ width: 56, height: 56, fontSize: 26 }}>А</div>
        </div>

        {/* Greeting */}
        <h1 style={{
          fontSize: 26, fontWeight: 700, color: '#0f172a',
          marginBottom: 20, textAlign: 'center', lineHeight: 1.3,
        }}>
          Здравствуйте,<br />{name}!
        </h1>

        {hasProgress ? (
          <div style={{
            background: '#eff6ff', border: '1px solid #bfdbfe',
            borderRadius: 12, padding: '16px 20px', marginBottom: 28,
          }}>
            <p style={{ fontSize: 15, color: '#1e40af', fontWeight: 600, marginBottom: 4 }}>
              У вас есть незавершённые ответы
            </p>
            <p style={{ fontSize: 14, color: '#3b82f6', margin: 0 }}>
              Продолжите с того места, где остановились — прогресс сохранён.
            </p>
          </div>
        ) : (
          <div style={{ marginBottom: 28 }}>
            <p style={{
              fontSize: 15, color: '#334155', lineHeight: 1.7,
              marginBottom: 14,
            }}>
              Пожалуйста, ответьте на вопросы о вашем поступлении в «Академию Будущего» в формате аудио сообщений. Для записи голоса нажмите на значок микрофона на следующем экране.
            </p>
            <p style={{
              fontSize: 15, color: '#334155', lineHeight: 1.7,
              marginBottom: 0,
            }}>
              Будем благодарны за подробные и развёрнутые ответы!
            </p>
          </div>
        )}

        {/* Stats row */}
        {!hasProgress && (
          <div style={{
            display: 'flex', gap: 12, marginBottom: 28,
          }}>
            <div style={{
              flex: 1, background: '#f8fafc', border: '1px solid #e2e8f0',
              borderRadius: 10, padding: '12px 16px', textAlign: 'center',
            }}>
              <p style={{ fontSize: 22, fontWeight: 700, color: '#102f6e', margin: 0 }}>{totalQuestions}</p>
              <p style={{ fontSize: 12, color: '#64748b', margin: 0 }}>вопросов</p>
            </div>
            <div style={{
              flex: 1, background: '#f8fafc', border: '1px solid #e2e8f0',
              borderRadius: 10, padding: '12px 16px', textAlign: 'center',
            }}>
              <p style={{ fontSize: 22, fontWeight: 700, color: '#102f6e', margin: 0 }}>~{Math.ceil(totalQuestions * 1.5)}</p>
              <p style={{ fontSize: 12, color: '#64748b', margin: 0 }}>минут</p>
            </div>
          </div>
        )}

        <button className="client-btn-primary client-btn-lg" onClick={onStart} style={{ width: '100%' }}>
          {hasProgress ? 'Продолжить' : 'Начать'}
        </button>
      </div>
    </div>
  )
}

function ThankYouScreen() {
  return (
    <div className="client-screen" style={{ justifyContent: 'center', textAlign: 'center' }}>
      <div style={{
        width: 72, height: 72, borderRadius: '9999px', background: '#dcfce7',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 24, marginLeft: 'auto', marginRight: 'auto',
      }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <h2 className="client-h2-brand">Спасибо!</h2>
      <p className="client-body-muted" style={{ maxWidth: 360 }}>
        Ваша анкета успешно отправлена. Мы свяжемся с вами в ближайшее время.
      </p>
    </div>
  )
}

function ReadonlyScreen({ data }: { data: InvitationData }) {
  return (
    <div className="client-screen" style={{ paddingTop: 32 }}>
      <div className="client-review">
        <div className="client-banner-amber">
          <p className="client-banner-title">Анкета уже заполнена</p>
          <p className="client-banner-sub">Редактирование недоступно. Ниже — ваши ответы.</p>
        </div>
        <h2 className="client-h2-brand" style={{ marginTop: 24 }}>Ваши ответы</h2>
        <div className="client-review-list">
          {data.questions.map((q) => {
            const resp = data.existing_responses.find((r: ExistingResponse) => r.question_id === q.id)
            return (
              <div key={q.id} className="client-review-item" style={{ cursor: 'default' }}>
                <p className="client-review-q">{q.order_index}. {q.text}</p>
                {resp?.transcription
                  ? <p className="client-review-a">{resp.transcription}</p>
                  : <p style={{ fontSize: 14, color: '#9ca3af' }}>Нет ответа</p>
                }
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
