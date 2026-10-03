import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'
import { getTabs } from './config/tabs'

describe('App tabs', () => {
  it('hides the demo tab when demo mode is off', () => {
    render(<App demoMode={false} />)
    expect(screen.getByRole('tab', { name: 'Zapytaj' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Mapa' })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Demo' })).not.toBeInTheDocument()
  })

  it('shows the demo tab with a simulation banner when demo mode is on', async () => {
    render(<App demoMode />)
    await userEvent.click(screen.getByRole('tab', { name: 'Demo' }))
    expect(screen.getByRole('status')).toHaveTextContent('Symulacja')
  })

  it('starts on the chat tab', () => {
    render(<App demoMode={false} />)
    expect(screen.getByRole('tab', { name: 'Zapytaj' })).toHaveAttribute('aria-selected', 'true')
  })

  it('builds tab list from the flag', () => {
    expect(getTabs(false).map((tab) => tab.id)).toEqual(['chat', 'map'])
    expect(getTabs(true).map((tab) => tab.id)).toEqual(['chat', 'map', 'demo'])
  })
})

describe('Emergency bar', () => {
  it('always shows a callable 112 link', () => {
    render(<App demoMode={false} />)
    expect(screen.getByRole('link', { name: /112/ })).toHaveAttribute('href', 'tel:112')
  })
})
