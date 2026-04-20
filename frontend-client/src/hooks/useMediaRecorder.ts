import { useCallback, useEffect, useRef, useState } from 'react'

export type RecordingState = 'idle' | 'requesting' | 'recording' | 'stopped' | 'error'

function getSupportedMimeType(): string {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/wav',
  ]
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

const MAX_DURATION_MS = 3 * 60 * 1000

export function useMediaRecorder() {
  const [state, setState] = useState<RecordingState>('idle')
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [mimeType, setMimeType] = useState('')
  const [elapsedMs, setElapsedMs] = useState(0)
  const [amplitude, setAmplitude] = useState(0)
  const [permissionDenied, setPermissionDenied] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animFrameRef = useRef<number>(0)
  const startTimeRef = useRef<number>(0)

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    cancelAnimationFrame(animFrameRef.current)
  }

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  const startRecording = useCallback(async () => {
    setState('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mime = getSupportedMimeType()
      setMimeType(mime)

      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
      mediaRecorderRef.current = mr
      chunksRef.current = []

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mime || 'audio/webm' })
        setAudioBlob(blob)
        setState('stopped')
        stopTimer()
        stopStream()
      }

      mr.start(250)
      startTimeRef.current = Date.now()
      setState('recording')

      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current
        setElapsedMs(elapsed)
        if (elapsed >= MAX_DURATION_MS) {
          mr.stop()
        }
      }, 200)

      const dataArr = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(dataArr)
        const avg = dataArr.reduce((a, b) => a + b, 0) / dataArr.length
        setAmplitude(avg / 255)
        animFrameRef.current = requestAnimationFrame(tick)
      }
      animFrameRef.current = requestAnimationFrame(tick)

      document.title = '🔴 Запись...'
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setPermissionDenied(true)
      }
      setState('error')
      stopStream()
    }
  }, [])

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop()
    document.title = 'Анкета'
  }, [])

  const reset = useCallback(() => {
    stopTimer()
    stopStream()
    setAudioBlob(null)
    setElapsedMs(0)
    setAmplitude(0)
    setState('idle')
    document.title = 'Анкета'
  }, [])

  useEffect(() => {
    return () => {
      stopTimer()
      stopStream()
      document.title = 'Анкета'
    }
  }, [])

  return {
    state,
    audioBlob,
    mimeType,
    elapsedMs,
    amplitude,
    permissionDenied,
    startRecording,
    stopRecording,
    reset,
  }
}
