import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  type InvitationDetail as IDetail,
  type InvitationNote,
  apiDelete,
  apiGet,
  apiPost,
  createNote,
  downloadFile,
  listNotes,
} from '../lib/api'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

function BlobAudio({ url, token }: { url: string; token: string | null }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
      })
      .catch(() => {})
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [url, token])

  if (!blobUrl) return <div className="text-xs text-gray-400 py-1">Загрузка аудио...</div>
  return <audio controls src={blobUrl} className="w-full mt-1" />
}

const TRANSCRIPTION_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  processing: 'Обрабатывается',
  done: 'Готово',
  failed: 'Ошибка',
}

const EXPORT_OPTIONS = [
  { value: 'csv_summary', label: 'CSV сводка' },
  { value: 'csv_rows', label: 'CSV построчно' },
  { value: 'xlsx_summary', label: 'XLSX сводка' },
  { value: 'xlsx_rows', label: 'XLSX построчно' },
  { value: 'pdf', label: 'PDF' },
]

/* ------------------------------------------------------------------ */
/*  Notes / chat panel                                                  */
/* ------------------------------------------------------------------ */
function NotesPanel({
  invitationId,
  token,
}: {
  invitationId: string
  token: string | null
}) {
  const [notes, setNotes] = useState<InvitationNote[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const messagesRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const prevCountRef = useRef(0)
  const initialLoadRef = useRef(false)

  const scrollToBottom = (smooth = true) => {
    const el = messagesRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  }

  const load = useCallback(async () => {
    if (!token) return
    try {
      const data = await listNotes(invitationId, token)
      const isFirst = !initialLoadRef.current
      const hasNew = data.length > prevCountRef.current
      prevCountRef.current = data.length
      initialLoadRef.current = true
      setNotes(data)
      // Скроллим только при первой загрузке или при новых сообщениях
      if (isFirst || hasNew) {
        setTimeout(() => scrollToBottom(!isFirst), 50)
      }
    } catch {}
  }, [invitationId, token])

  useEffect(() => {
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [load])

  const handleSend = async () => {
    const trimmed = text.trim()
    if (!trimmed || !token || sending) return
    setSending(true)
    setSendError('')
    try {
      const note = await createNote(invitationId, trimmed, token)
      prevCountRef.current += 1
      setNotes((prev) => [...prev, note])
      setText('')
      setTimeout(() => scrollToBottom(), 50)
    } catch (e: any) {
      setSendError(e?.message || 'Ошибка отправки')
    } finally {
      setSending(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const fmt = (iso: string) =>
    new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex-shrink-0">
        <h3 className="text-sm font-semibold text-gray-700">Заметки и чат</h3>
        <p className="text-xs text-gray-400 mt-0.5">Enter — отправить · Shift+Enter — перенос</p>
      </div>

      {/* Messages */}
      <div ref={messagesRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
        {notes.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-6">Заметок пока нет</p>
        )}
        {notes.map((note) => (
          <div key={note.id}>
            <p className="text-xs text-gray-400 mb-1">
              {note.manager_name} · {fmt(note.created_at)}
            </p>
            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2 leading-relaxed whitespace-pre-wrap">
              {note.text}
            </p>
          </div>
        ))}
      </div>

      {/* Input */}
      {sendError && (
        <p className="px-4 pb-1 text-xs text-red-500 flex-shrink-0">{sendError}</p>
      )}
      <div className="px-4 py-3 border-t border-gray-200 flex-shrink-0 flex gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Напишите заметку..."
          rows={2}
          className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-[inherit] leading-snug"
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || sending}
          className="btn-primary self-end px-3 py-2 text-sm disabled:opacity-40"
          title="Отправить"
        >
          ↑
        </button>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main detail page                                                    */
/* ------------------------------------------------------------------ */
export default function InvitationDetail() {
  const { id } = useParams<{ id: string }>()
  const { accessToken } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState<IDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [exportOpen, setExportOpen] = useState(false)
  const [copyDone, setCopyDone] = useState(false)
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async () => {
    if (!accessToken || !id) return
    try {
      const res = await apiGet(`/api/invitations/${id}`, accessToken)
      setData(res)
    } catch {
      navigate('/')
    } finally {
      setLoading(false)
    }
  }, [accessToken, id, navigate])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!data) return
    const hasPending = data.responses.some(
      (r) => r.transcription_status === 'pending' || r.transcription_status === 'processing',
    )
    if (hasPending) {
      autoRefreshRef.current = setInterval(load, 10_000)
    }
    return () => {
      if (autoRefreshRef.current) clearInterval(autoRefreshRef.current)
    }
  }, [data, load])

  const handleDelete = async () => {
    if (!accessToken || !id) return
    setDeleteLoading(true)
    setDeleteError('')
    try {
      await apiDelete(`/api/invitations/${id}`, accessToken)
      navigate('/')
    } catch (e: any) {
      setDeleteError(e?.message || 'Ошибка удаления')
      setDeleteConfirm(false)
      setDeleteLoading(false)
    }
  }

  const handleRetranscribe = async (responseId: string) => {
    if (!accessToken) return
    await apiPost(`/api/admin/responses/${responseId}/retranscribe`, null, accessToken)
    load()
  }

  const handleExport = async (format: string) => {
    if (!accessToken || !id) return
    setExportOpen(false)
    await downloadFile(`/api/invitations/${id}/export?format=${format}`, accessToken)
  }

  const handleCopy = () => {
    if (!data) return
    const respMap = Object.fromEntries(data.responses.map((r) => [r.question_id, r]))
    const fmtDate = (iso: string | null) =>
      iso ? new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

    const lines: string[] = [
      `Клиент: ${data.client_name}`,
      `Телефон: ${data.client_phone || '—'}`,
      `Менеджер: ${data.manager_full_name}`,
      `Заполнено: ${fmtDate(data.completed_at)}`,
      '',
      '─'.repeat(40),
      '',
    ]

    data.questions.forEach((q, idx) => {
      const resp = respMap[q.id]
      const answer = resp?.transcription || '—'
      lines.push(`Вопрос ${idx + 1}: ${q.text}`)
      lines.push(`Ответ: ${answer}`)
      lines.push('')
    })

    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      setCopyDone(true)
      setTimeout(() => setCopyDone(false), 2000)
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!data) return null

  const respMap = Object.fromEntries(data.responses.map((r) => [r.question_id, r]))

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-200 px-4 sm:px-6 py-3 flex items-center gap-3">
        <Link to="/" className="text-gray-400 hover:text-primary text-sm whitespace-nowrap">
          ← Назад
        </Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-medium text-gray-700 truncate">{data.client_name}</span>
      </nav>

      {/* Two-column layout: responses | notes */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex flex-col lg:flex-row gap-6">

        {/* LEFT: header card + response cards */}
        <div className="flex-1 min-w-0 space-y-4">

          {/* Header card */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div className="min-w-0">
                <h1 className="text-xl font-bold text-gray-900">{data.client_name}</h1>
                <p className="text-gray-500 text-sm">{data.client_phone || '—'}</p>
                {data.client_note && (
                  <p className="text-gray-400 text-sm mt-1 italic">{data.client_note}</p>
                )}
                <p className="text-sm text-gray-500 mt-2">
                  Менеджер: {data.manager_full_name} · Статус:{' '}
                  <span className={`badge-${data.status}`}>{data.status}</span>
                </p>
                {data.completed_at && (
                  <p className="text-xs text-gray-400 mt-1">
                    Заполнено: {new Date(data.completed_at).toLocaleString('ru-RU')}
                  </p>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={handleCopy}
                  className="btn-secondary text-sm"
                  title="Скопировать результаты в буфер обмена"
                >
                  {copyDone ? '✓ Скопировано' : 'Скопировать'}
                </button>

                <div className="relative">
                  <button
                    onClick={() => setExportOpen(!exportOpen)}
                    className="btn-secondary text-sm"
                  >
                    Экспорт ▾
                  </button>
                  {exportOpen && (
                    <div className="absolute right-0 mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                      {EXPORT_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => handleExport(opt.value)}
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {deleteError && (
                  <span className="text-xs text-red-500">{deleteError}</span>
                )}
                {!deleteConfirm ? (
                  <button
                    onClick={() => { setDeleteError(''); setDeleteConfirm(true) }}
                    className="text-sm border border-red-300 text-red-500 px-3 py-2 rounded-lg hover:bg-red-50"
                  >
                    Удалить
                  </button>
                ) : (
                  <div className="flex gap-2 items-center flex-wrap">
                    <span className="text-sm text-red-600">Удалить «{data.client_name}»?</span>
                    <button
                      onClick={handleDelete}
                      disabled={deleteLoading}
                      className="text-sm bg-red-500 text-white px-3 py-1.5 rounded-lg disabled:opacity-60"
                    >
                      {deleteLoading ? '...' : 'Да'}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(false)}
                      disabled={deleteLoading}
                      className="text-sm border px-3 py-1.5 rounded-lg disabled:opacity-60"
                    >
                      Отмена
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Response cards */}
          {data.questions.map((q, idx) => {
            const resp = respMap[q.id]
            return (
              <div key={q.id} className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="font-semibold text-gray-800 mb-3">
                  {idx + 1}. {q.text}
                </p>
                {resp ? (
                  <>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className={`badge-${resp.transcription_status}`}>
                        {TRANSCRIPTION_LABELS[resp.transcription_status] ||
                          resp.transcription_status}
                      </span>
                      {resp.audio_duration_sec && (
                        <span className="text-xs text-gray-400">
                          {resp.audio_duration_sec.toFixed(1)} сек
                        </span>
                      )}
                      {resp.transcription_status === 'failed' && (
                        <button
                          onClick={() => handleRetranscribe(resp.id)}
                          className="text-xs text-primary underline ml-auto"
                        >
                          Перетранскрибировать
                        </button>
                      )}
                    </div>
                    {resp.audio_url && (
                      <BlobAudio
                        url={`${BASE}${resp.audio_url}`}
                        token={accessToken}
                      />
                    )}
                    {resp.transcription && (
                      <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 leading-relaxed mt-2">
                        {resp.transcription}
                      </p>
                    )}
                    {resp.transcription_status === 'failed' && resp.transcription_error && (
                      <p className="text-xs text-red-500 mt-1">{resp.transcription_error}</p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-gray-400">Нет ответа</p>
                )}
              </div>
            )
          })}
        </div>

        {/* RIGHT: notes/chat panel */}
        <div className="lg:w-72 xl:w-80 flex-shrink-0">
          <div
            className="bg-white rounded-xl border border-gray-200 lg:sticky lg:top-4 flex flex-col"
            style={{ height: 'clamp(360px, calc(100vh - 120px), 700px)' }}
          >
            <NotesPanel invitationId={id!} token={accessToken} />
          </div>
        </div>
      </div>
    </div>
  )
}
