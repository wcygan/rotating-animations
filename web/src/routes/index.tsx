import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: Home })

const ANIMATIONS = [
  { to: '/glizzy', label: 'glizzy', desc: 'an ascii hot dog rotating around a vertical axis' },
  { to: '/teacup', label: 'teacup', desc: 'an ascii cup of tea spinning on its saucer' },
  { to: '/mallard', label: 'mallard', desc: 'an ascii mallard duck pivoting on the spot' },
] as const

function Home() {
  return (
    <main className="hub">
      <h1 className="hub-title">rotating animations</h1>
      <ul className="hub-list">
        {ANIMATIONS.map((a) => (
          <li key={a.to}>
            <Link to={a.to} className="hub-link">
              <span className="hub-link-label">{a.label}</span>
              <span className="hub-link-desc">{a.desc}</span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  )
}
