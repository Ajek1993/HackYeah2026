import { useRef, useState } from 'react'
import { ChatView } from './components/ChatView'
import { DemoView } from './components/DemoView'
import { EmergencyBar } from './components/EmergencyBar'
import { Logo } from './components/Logo'
import { MapView } from './components/MapView'
import { SimulationBanner } from './components/SimulationBanner'
import { TabNav, type TabId } from './components/TabNav'
import { config } from './config/env'
import { findScenario } from './config/demo'
import { getTabs } from './config/tabs'
import { useDemo } from './hooks/useDemo'

type Props = {
  demoMode?: boolean
}

export default function App({ demoMode = config.demoMode }: Props) {
  const [active, setActive] = useState<TabId>('chat')
  const tabs = getTabs(demoMode)
  const demo = useDemo(demoMode)
  const scenario = findScenario(demo.active)
  // A new scenario means new data: chat and map start over (keyed remount)
  const dataKey = scenario?.id ?? 'live'
  const mainRef = useRef<HTMLElement>(null)

  function openTab(id: TabId) {
    setActive(id)
    // The button that opened the tab disappears with the Demo panel; keep focus in the page
    mainRef.current?.focus()
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-3 focus:font-semibold"
      >
        Przejdź do treści
      </a>
      {demoMode && <SimulationBanner demo={demo} />}
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between lg:gap-8">
          <Logo />
          <div className="lg:w-[28rem]">
            <TabNav tabs={tabs} active={active} onChange={setActive} />
          </div>
        </div>
      </header>

      <main
        ref={mainRef}
        id="main"
        tabIndex={-1}
        className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 lg:py-10"
      >
        {/* Chat stays mounted while hidden, so the conversation survives a visit to the map */}
        <div id="panel-chat" role="tabpanel" aria-labelledby="tab-chat" hidden={active !== 'chat'}>
          <ChatView key={dataKey} quickQuestions={scenario?.questions} />
        </div>
        {active === 'map' && (
          <div id="panel-map" role="tabpanel" aria-labelledby="tab-map">
            <MapView key={dataKey} />
          </div>
        )}
        {active === 'demo' && demoMode && (
          <div id="panel-demo" role="tabpanel" aria-labelledby="tab-demo">
            <DemoView demo={demo} onOpenTab={openTab} />
          </div>
        )}
      </main>

      <EmergencyBar />
    </div>
  )
}
