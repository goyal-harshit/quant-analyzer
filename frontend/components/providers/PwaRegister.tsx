'use client'

import { useEffect } from 'react'

export default function PwaRegister() {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''
    const swUrl = `${basePath}/sw.js`
    const scope = `${basePath || ''}/`

    navigator.serviceWorker.register(swUrl, { scope })
      .then((registration) => registration.update())
      .catch(() => {
        // PWA support should never block the app shell.
      })

    if ('caches' in window) {
      caches.keys()
        .then((keys) => Promise.all(
          keys
            .filter((key) => key.startsWith('quantai-shell-') && key !== 'quantai-shell-v2')
            .map((key) => caches.delete(key))
        ))
        .catch(() => {})
    }
  }, [])

  return null
}
