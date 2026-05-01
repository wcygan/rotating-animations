// effect-ts skipped: no server-side business logic; this is a static page
// that imports a JSON flipbook and animates it with requestAnimationFrame.
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import frames from '#/parrot.json'

export const Route = createFileRoute('/parrot')({ component: Parrot })

const FRAME_KEYS = Object.keys(frames as Record<string, string[]>)
const FRAME_LIST = FRAME_KEYS.map((k) => (frames as Record<string, string[]>)[k])
const FRAME_MS = 50 // 60 frames * 50ms = 3s rotation

function Parrot() {
  const [i, setI] = useState(0)
  const lastRef = useRef(0)

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let raf = 0
    const tick = (t: number) => {
      if (t - lastRef.current >= FRAME_MS) {
        setI((j) => (j + 1) % FRAME_LIST.length)
        lastRef.current = t
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  const lines = FRAME_LIST[i]

  return (
    <main className="parrot-page">
      <pre className="parrot" aria-hidden="true">
        {lines.map((line, k) => (
          <div key={k} dangerouslySetInnerHTML={{ __html: line || '&nbsp;' }} />
        ))}
      </pre>
      <p className="tagline">a rotating parrot</p>
    </main>
  )
}
