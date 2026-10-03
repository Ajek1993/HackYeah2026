import type { TabDef } from '../components/TabNav'

export function getTabs(demoMode: boolean): TabDef[] {
  const tabs: TabDef[] = [
    { id: 'chat', label: 'Zapytaj' },
    { id: 'map', label: 'Mapa' },
  ]
  // Demo exists only in the presentation build (US-06)
  if (demoMode) tabs.push({ id: 'demo', label: 'Demo' })
  return tabs
}
