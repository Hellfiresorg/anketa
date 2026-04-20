import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiPost } from '../lib/api'

export default function SetupNamePage() {
  const { accessToken, manager, setManager } = useAuth()
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (!accessToken) {
    navigate('/login', { replace: true })
    return null
  }
  if (manager?.full_name) {
    navigate('/', { replace: true })
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) {
      setError('Введите хотя бы одно слово')
      return
    }
    setError('')
    setLoading(true)
    try {
      const data = await apiPost('/api/me/name', { full_name: trimmed }, accessToken, 'PATCH')
      setManager({ ...manager!, full_name: data.full_name })
      navigate('/', { replace: true })
    } catch {
      setError('Не удалось сохранить. Попробуйте ещё раз.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <img
            src="/brand/logo.svg"
            alt="logo"
            className="h-10"
            onError={(e) => (e.currentTarget.style.display = 'none')}
          />
        </div>
        <h1 className="text-2xl font-bold text-primary text-center mb-2">Добро пожаловать!</h1>
        <p className="text-gray-500 text-sm text-center mb-6">Как вас записать? Это спросим один раз.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ваше имя</label>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoFocus
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Иванов Иван или Иванов И.И."
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Сохранение...' : 'Продолжить'}
          </button>
        </form>
      </div>
    </div>
  )
}
