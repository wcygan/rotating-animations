import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: Home })

const ANIMATIONS = [
  { to: '/glizzy', label: 'glizzy', desc: 'an ascii hot dog rotating around a vertical axis' },
  { to: '/teacup', label: 'teacup', desc: 'an ascii cup of tea spinning on its saucer' },
  { to: '/mallard', label: 'mallard', desc: 'an ascii mallard duck pivoting on the spot' },
  { to: '/duck', label: 'duck', desc: 'a low-poly stylized duck spinning slowly' },
  { to: '/parrot', label: 'parrot', desc: 'an ascii parrot turning in place' },
  { to: '/penguin', label: 'penguin', desc: 'an ascii penguin pivoting on its feet' },
  { to: '/toucan', label: 'toucan', desc: 'an ascii toco toucan with an oversized beak' },
  { to: '/hummingbird', label: 'hummingbird', desc: 'an ascii hummingbird hovering and turning' },
  { to: '/goose', label: 'goose', desc: 'an ascii goose pivoting on the spot' },
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
