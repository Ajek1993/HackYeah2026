import { useState } from 'react'
import { ChatView } from './components/ChatView'
import { DemoView } from './components/DemoView'
import { EmergencyBar } from './components/EmergencyBar'
import { Logo } from './components/Logo'
import { MapView } from './components/MapView'
import { TabNav, type TabId } from './components/TabNav'
import { config } from './config/env'
import { getTabs } from './config/tabs'

type Props = {
  demoMode?: boolean
}

export default function App({ demoMode = config.demoMode }: Props) {
  const [active, setActive] = useState<TabId>('chat')
  const tabs = getTabs(demoMode)

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-4">
          <Logo />
          <TabNav tabs={tabs} active={active} onChange={setActive} />
        </div>
      </header>

      <main
        id={`panel-${active}`}
        role="tabpanel"
        aria-labelledby={`tab-${active}`}
        className="mx-auto w-full max-w-3xl flex-1 px-4 py-8"
      >
        {active === 'chat' && <ChatView />}
        {active === 'map' && <MapView />}
        {active === 'demo' && demoMode && <DemoView />}
      </main>

      <EmergencyBar />
    </div>
  )
}
