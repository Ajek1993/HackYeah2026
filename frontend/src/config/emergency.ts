export type EmergencyNumber = {
  number: string
  name: string
}

export const PRIMARY_EMERGENCY: EmergencyNumber = { number: '112', name: 'Numer alarmowy' }

export const OTHER_EMERGENCY: EmergencyNumber[] = [
  { number: '999', name: 'Pogotowie ratunkowe' },
  { number: '998', name: 'Straż pożarna' },
  { number: '991', name: 'Pogotowie energetyczne' },
  { number: '992', name: 'Pogotowie gazowe' },
  { number: '993', name: 'Pogotowie ciepłownicze' },
  { number: '994', name: 'Pogotowie wodociągowe' },
]

export const DISCLAIMER =
  'KryzIO nie zastępuje komunikatów służb. Nadrzędny jest państwowy system ostrzegania (RCB, 112) — KryzIO jest jego uzupełnieniem i wsparciem w komunikacji.'
