import { HeadContent, Link, Scripts, createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import appCss from '../styles.css?url'

const TABS = [
  { to: '/', label: 'home' },
  { to: '/glizzy', label: 'glizzy' },
  { to: '/teacup', label: 'teacup' },
  { to: '/mallard', label: 'mallard' },
] as const

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'rotating animations',
      },
      {
        name: 'description',
        content: 'a collection of rotating ascii animations',
      },
    ],
    links: [
      {
        rel: 'stylesheet',
        href: appCss,
      },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        <nav className="tabs" aria-label="animations">
          {TABS.map((t) => (
            <Link
              key={t.to}
              to={t.to}
              className="tab"
              activeOptions={{ exact: t.to === '/' }}
              activeProps={{ className: 'tab tab-active' }}
            >
              {t.label}
            </Link>
          ))}
        </nav>
        {children}
        <TanStackDevtools
          config={{
            position: 'bottom-right',
          }}
          plugins={[
            {
              name: 'Tanstack Router',
              render: <TanStackRouterDevtoolsPanel />,
            },
          ]}
        />
        <Scripts />
      </body>
    </html>
  )
}
