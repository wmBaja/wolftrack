import { reactive } from 'vue'

export interface DialogButton {
  id: string          // what the promise resolves with when clicked
  text: string
  danger?: boolean    // red styling
  primary?: boolean   // filled accent styling
}

export interface DialogOptions {
  title: string
  body: string
  buttons: DialogButton[]
  danger?: boolean    // styles the eyebrow label
  eyebrow?: string    // optional override for the small label above the title
}

export const dialogState = reactive({
  open: false,
  options: null as DialogOptions | null,
})

let resolver: ((id: string) => void) | null = null

export function showDialog(options: DialogOptions): Promise<string> {
  // If another dialog is already open, resolve it as dismissed first
  resolver?.('dismissed')

  dialogState.options = options
  dialogState.open = true

  return new Promise<string>((resolve) => {
    resolver = resolve
  })
}

export function closeDialog(result = 'dismissed'): void {
  dialogState.open = false   // keep options so the fade-out still shows text
  resolver?.(result)
  resolver = null
}

// Convenience wrapper for the common confirm/cancel case
export async function confirmDialog(
  title: string,
  body: string,
  opts: { confirmText?: string; cancelText?: string; danger?: boolean } = {},
): Promise<boolean> {
  const { confirmText = 'Confirm', cancelText = 'Cancel', danger = false } = opts

  const result = await showDialog({
    title,
    body,
    danger,
    buttons: [
      { id: 'cancel', text: cancelText },
      { id: 'confirm', text: confirmText, danger, primary: !danger },
    ],
  })

  return result === 'confirm'
}
