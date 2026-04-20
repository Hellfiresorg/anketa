import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { type Template, apiGet, apiPost } from '../lib/api'

export default function CreateInvitation() {
  const { accessToken } = useAuth()
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<Template[]>([])
  const [templateId, setTemplateId] = useState('')
  const [clientName, setClientName] = useState('')
  const [clientPhone, setClientPhone] = useState('')
  const [clientNote, setClientNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState<{ id: string; url: string } | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!accessToken) return
    apiGet('/api/templates', accessToken)
      .then((t: Template[]) => {
        setTemplates(t)
        if (t.length > 0) setTemplateId(t[0].id)
      })
      .catch((e: any) => {
        if (e?.status === 401) navigate('/login')
        else setError('Не удалось загрузить шаблоны')
      })
  }, [accessToken])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!accessToken) return
    setError('')
    setLoading(true)
    try {
      const res = await apiPost('/api/invitations', {
        template_id: templateId,
        client_name: clientName,
        client_phone: clientPhone || null,
        client_note: clientNote || null,
      }, accessToken)
      setCreated(res)
    } catch (err: any) {
      setError(err?.message || 'Ошибка создания анкеты')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (created) {
      navigator.clipboard.writeText(created.url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <Link to="/" className="text-gray-400 hover:text-primary text-sm">← Назад</Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-medium text-gray-700">Новая анкета</span>
      </nav>

      <div className="max-w-lg mx-auto px-6 py-8">
        {!created ? (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h1 className="text-xl font-bold text-gray-900 mb-6">Создать приглашение</h1>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Шаблон анкеты</label>
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {templates.length === 0 && (
                    <option value="" disabled>Загрузка...</option>
                  )}
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Имя клиента *</label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Иван Иванов"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Телефон</label>
                <input
                  type="tel"
                  value={clientPhone}
                  onChange={(e) => setClientPhone(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="+7 999 000 0000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Заметка (внутренняя)</label>
                <textarea
                  value={clientNote}
                  onChange={(e) => setClientNote(e.target.value)}
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  placeholder="Пришёл с рекламы Instagram..."
                />
              </div>
              {error && <p className="text-red-500 text-sm">{error}</p>}
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Создание...' : 'Создать'}
              </button>
            </form>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Приглашение создано!</h2>
            <p className="text-sm text-gray-500 mb-4">Отправьте эту ссылку клиенту:</p>
            <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm font-mono text-gray-700 break-all mb-4">
              {created.url}
            </div>
            <div className="flex gap-3 justify-center">
              <button onClick={handleCopy} className="btn-primary">
                {copied ? '✓ Скопировано' : 'Скопировать'}
              </button>
              <a href={created.url} target="_blank" rel="noopener noreferrer" className="btn-secondary">
                Открыть
              </a>
            </div>
            <button
              onClick={() => navigate(`/invitations/${created.id}`)}
              className="block w-full text-center text-sm text-primary underline mt-4"
            >
              Перейти к анкете
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
