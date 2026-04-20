import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiPost } from '../lib/api'

export default function Settings() {
  const { accessToken, manager } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (newPassword !== confirm) {
      setError('Пароли не совпадают')
      return
    }
    if (newPassword.length < 8) {
      setError('Пароль должен быть не менее 8 символов')
      return
    }
    setLoading(true)
    try {
      await apiPost('/api/me/password', { current_password: currentPassword, new_password: newPassword }, accessToken)
      setSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirm('')
    } catch (err: any) {
      setError(err?.message || 'Ошибка смены пароля')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <Link to="/" className="text-gray-400 hover:text-primary text-sm">← Назад</Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-medium text-gray-700">Настройки</span>
      </nav>

      <div className="max-w-md mx-auto px-6 py-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h1 className="text-xl font-bold text-gray-900 mb-1">Настройки</h1>
          <p className="text-sm text-gray-500 mb-6">{manager?.email}</p>

          <h2 className="text-base font-semibold text-gray-800 mb-4">Сменить пароль</h2>
          {success && (
            <div className="bg-green-50 text-green-700 rounded-lg px-4 py-3 text-sm mb-4">
              Пароль успешно изменён
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Текущий пароль</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Новый пароль</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Подтверждение</label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Сохранение...' : 'Сменить пароль'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
