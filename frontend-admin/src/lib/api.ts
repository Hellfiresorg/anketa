const BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function apiPost(
  path: string,
  body: unknown,
  token: string | null,
  method = 'POST',
): Promise<any> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== null ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    if (res.status === 401) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_manager')
      window.location.href = '/login'
    }
    throw Object.assign(new Error(err?.detail || res.statusText), { status: res.status })
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res
}

export async function apiGet(path: string, token: string | null): Promise<any> {
  return apiPost(path, null, token, 'GET')
}

export async function apiDelete(path: string, token: string | null): Promise<void> {
  await apiPost(path, null, token, 'DELETE')
}

export async function downloadFile(path: string, token: string | null): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('Download failed')
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const match = cd.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : 'export'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export interface Template {
  id: string
  name: string
}

export interface InvitationRow {
  id: string
  client_name: string
  client_phone: string | null
  manager_full_name: string
  status: string
  created_at: string
  completed_at: string | null
  transcription_ready: number
  transcription_total: number
}

export interface InvitationListResponse {
  items: InvitationRow[]
  total: number
  page: number
  page_size: number
}

export interface ResponseDetail {
  id: string
  question_id: string
  audio_url: string | null
  audio_duration_sec: number | null
  transcription: string | null
  transcription_status: string
  transcription_error: string | null
  created_at: string
}

export interface InvitationNote {
  id: string
  text: string
  manager_name: string
  created_at: string
}

export async function listNotes(invitationId: string, token: string | null): Promise<InvitationNote[]> {
  return apiGet(`/api/invitations/${invitationId}/notes`, token)
}

export async function createNote(invitationId: string, text: string, token: string | null): Promise<InvitationNote> {
  return apiPost(`/api/invitations/${invitationId}/notes`, { text }, token)
}

export interface QuestionDetail {
  id: string
  order_index: number
  text: string
  hint: string | null
  is_required: boolean
}

export interface InvitationDetail {
  id: string
  client_name: string
  client_phone: string | null
  client_note: string | null
  manager_full_name: string
  status: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  template_id: string
  questions: QuestionDetail[]
  responses: ResponseDetail[]
}
