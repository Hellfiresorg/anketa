import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { type InvitationListResponse, type InvitationRow, apiGet } from '../lib/api'

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  in_progress: 'Заполняется',
  completed: 'Заполнено',
}

export default function Dashboard() {
  const { accessToken, manager, logout } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState<InvitationListResponse | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [myOnly, setMyOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!accessToken) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (statusFilter) params.set('status', statusFilter)
      if (myOnly) params.set('my_only', 'true')
      params.set('page', String(page))
      params.set('page_size', '20')
      const res = await apiGet(`/api/invitations?${params}`, accessToken)
      setData(res)
    } catch {
    } finally {
      setLoading(false)
    }
  }, [accessToken, search, statusFilter, myOnly, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/brand/logo.svg" alt="logo" className="h-8" onError={(e) => (e.currentTarget.style.display = 'none')} />
          <span className="font-semibold text-primary text-lg">Анкеты</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{manager?.full_name}</span>
          <Link to="/settings" className="text-sm text-gray-500 hover:text-primary">Настройки</Link>
          <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">Выйти</button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <input
            type="text"
            placeholder="Поиск по имени или телефону..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="border border-gray-300 rounded-lg px-3 py-2 flex-1 focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">Все статусы</option>
            <option value="pending">Ожидает</option>
            <option value="in_progress">Заполняется</option>
            <option value="completed">Заполнено</option>
          </select>
          <div className="flex items-center gap-2 border border-gray-300 rounded-lg px-3 py-2 bg-white">
            <button
              onClick={() => setMyOnly(false)}
              className={`text-sm px-2 py-0.5 rounded ${!myOnly ? 'bg-primary text-white' : 'text-gray-600'}`}
            >Все</button>
            <button
              onClick={() => setMyOnly(true)}
              className={`text-sm px-2 py-0.5 rounded ${myOnly ? 'bg-primary text-white' : 'text-gray-600'}`}
            >Мои</button>
          </div>
          <Link to="/invitations/new" className="btn-primary whitespace-nowrap">
            + Создать анкету
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden admin-table-wrap">
              <table className="w-full text-sm min-w-[600px]">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Клиент</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Телефон</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Менеджер</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Транскрипции</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Создано</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((inv) => (
                    <tr
                      key={inv.id}
                      onClick={() => navigate(`/invitations/${inv.id}`)}
                      className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    >
                      <td className="px-4 py-3 font-medium text-gray-900">{inv.client_name}</td>
                      <td className="px-4 py-3 text-gray-500">{inv.client_phone || '—'}</td>
                      <td className="px-4 py-3 text-gray-500">{inv.manager_full_name}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={inv.status} />
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {inv.transcription_ready}/{inv.transcription_total}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {new Date(inv.created_at).toLocaleDateString('ru-RU')}
                      </td>
                    </tr>
                  ))}
                  {data?.items.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-gray-400">
                        Анкет не найдено
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {data && data.total > 20 && (
              <div className="flex justify-center gap-3 mt-4">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="btn-secondary disabled:opacity-40"
                >← Назад</button>
                <span className="text-sm text-gray-500 py-2">
                  Страница {page} из {Math.ceil(data.total / 20)}
                </span>
                <button
                  disabled={page * 20 >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                  className="btn-secondary disabled:opacity-40"
                >Вперёд →</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge-${status}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}
