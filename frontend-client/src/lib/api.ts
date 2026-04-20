const BASE = import.meta.env.VITE_API_BASE_URL || ''

export interface Question {
  id: string
  order_index: number
  text: string
  hint: string | null
  is_required: boolean
}

export interface ExistingResponse {
  question_id: string
  transcription_status: string
  audio_url: string
  transcription: string | null
}

export interface InvitationData {
  invitation: {
    id: string
    client_name: string
    status: string
    started_at: string | null
    completed_at: string | null
  }
  questions: Question[]
  existing_responses: ExistingResponse[]
}

export async function getInvitation(id: string): Promise<InvitationData> {
  const res = await fetch(`${BASE}/api/public/invitations/${id}`)
  if (res.status === 404) throw new Error('NOT_FOUND')
  if (res.status === 410) throw new Error('GONE')
  if (!res.ok) throw new Error('SERVER_ERROR')
  return res.json()
}

export async function submitTextResponse(
  invitationId: string,
  questionId: string,
  text: string,
): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/api/public/invitations/${invitationId}/responses/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, text }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw Object.assign(new Error('SUBMIT_FAILED'), { status: res.status, detail: err })
  }
  return res.json()
}

export async function submitInvitation(invitationId: string) {
  const res = await fetch(`${BASE}/api/public/invitations/${invitationId}/submit`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw Object.assign(new Error('SUBMIT_FAILED'), { status: res.status, detail: err })
  }
  return res.json()
}
