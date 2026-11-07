// ── Lumi — useToast composable ────────────────────────────────────────────
// Global toast notifications. Call from anywhere:
//   const toast = useToast()
//   toast.success('Word added to the dictionary')
//   toast.error('Something went wrong')
//   toast.info('Suggestion rejected')
//   toast.success('Accepted', { action: { label: 'Undo', fn: undoFn } })
//
// State lives in useState() so every component instance shares one queue.
// Rendering is done by <AppToaster /> (mounted once in app.vue).

export interface ToastAction {
  label: string
  fn: () => void | Promise<void>
}

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
  action?: ToastAction
}

export interface ToastOptions {
  /** Auto-dismiss after N ms. Default 4000; errors stay 6000. Use 0 to disable. */
  duration?: number
  /** Optional inline action button (e.g. "Undo"). */
  action?: ToastAction
}

const MAX_TOASTS = 4

export function useToast() {
  const toasts = useState<ToastItem[]>('lumi-toasts', () => [])

  let seq = 0

  function dismiss(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function show(type: ToastType, message: string, opts: ToastOptions = {}): number {
    // Toasts are client-only — skip silently during SSR
    if (!import.meta.client) return -1

    const id = ++seq
    const duration = opts.duration ?? (type === 'error' ? 6000 : 4000)

    toasts.value = [...toasts.value, { id, type, message, action: opts.action }]
    // Keep the stack short — drop the oldest
    if (toasts.value.length > MAX_TOASTS) {
      toasts.value = toasts.value.slice(-MAX_TOASTS)
    }
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration)
    }
    return id
  }

  return {
    toasts,
    dismiss,
    success: (msg: string, opts?: ToastOptions) => show('success', msg, opts),
    error: (msg: string, opts?: ToastOptions) => show('error', msg, opts),
    info: (msg: string, opts?: ToastOptions) => show('info', msg, opts),
  }
}
