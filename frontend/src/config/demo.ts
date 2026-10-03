// Presentation scenarios; ids match api/app/demo/scenarios.py

export type DemoScenario = {
  id: string
  title: string
  summary: string
  changes: string[]
  questions: string[]
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'flood',
    title: 'Powódź',
    summary: 'Wisła w Krakowie przekracza stan alarmowy po dobie ulewnych opadów.',
    changes: [
      'Ostrzeżenie hydrologiczne 3. stopnia',
      'Wisła w Bielanach 585 cm (alarmowy 520)',
      'Awaria prądu na Dębnikach',
    ],
    questions: [
      'Czy na Kobierzyńskiej grozi zalanie?',
      'Woda podchodzi pod dom. Co robić?',
      'Co spakować na wypadek ewakuacji?',
    ],
  },
  {
    id: 'power_outage',
    title: 'Brak prądu',
    summary: 'Silny wiatr zrywa linie energetyczne w kilku dzielnicach.',
    changes: ['Ostrzeżenie przed silnym wiatrem', 'Trzy awarie: Nowa Huta, Krowodrza, Podgórze'],
    questions: [
      'Czy w Nowej Hucie jest prąd?',
      'Nie mam prądu od rana. Co robić?',
      'Jak przechować leki w lodówce bez prądu?',
    ],
  },
  {
    id: 'bomb_threat',
    title: 'Atak bombowy',
    summary: 'Ogłoszono alarm o zagrożeniu atakiem z powietrza dla całego Krakowa.',
    changes: ['Alarm 3. stopnia dla Krakowa', 'Prawdziwe schrony i miejsca ukrycia na mapie'],
    questions: [
      'Ogłoszono alarm. Co mam robić i gdzie jest najbliższy schron?',
      'Gdzie się schować w okolicy Rynku Głównego?',
      'Jestem z dziećmi w domu. Co robić?',
    ],
  },
]

export const findScenario = (id: string | null) =>
  DEMO_SCENARIOS.find((scenario) => scenario.id === id) ?? null
