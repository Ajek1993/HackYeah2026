// Fallback for the "Dzwoń 112" banner when the agent is slow or unavailable (PRD story 3).
// Matched against the question without diacritics, so "pozar" and "pożar" both count.
// Phrases describe something happening now, so preparedness questions
// ("jak się przygotować na pożar?") do not trigger the banner.
const KEYWORDS = [
  'woda wlewa',
  'wlewa sie woda',
  'zalewa nas',
  'zalewa mi',
  'zalalo nas',
  'zalalo mi',
  'jestesmy zalani',
  'tonie',
  'topi sie',
  'pali sie',
  'plonie',
  'mam pozar',
  'jest pozar',
  'pozar w',
  'dym w',
  'wybuchl',
  'slychac wybuch',
  'byl wybuch',
  'gaz sie ulatnia',
  'ulatnia sie gaz',
  'czuc gaz',
  'zapach gazu',
  'ranny',
  'ranna',
  'ranni',
  'krwawi',
  'nie oddycha',
  'nieprzytomn',
  'zawal',
  'zemdlal',
  'porazenie pradem',
  'uwiezion',
  'nie moze wyjsc',
  'nie moze zejsc',
  'strzelanin',
  'strzelaja',
  'podlozono bomb',
  'zaatakowa',
  'ratunku',
]

export function normalize(text: string): string {
  return text.toLowerCase().replace(/ł/g, 'l').normalize('NFD').replace(/[̀-ͯ]/g, '')
}

export function looksLikeEmergency(text: string): boolean {
  const normalized = normalize(text)
  return KEYWORDS.some((keyword) => normalized.includes(keyword))
}
