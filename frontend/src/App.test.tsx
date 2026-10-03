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
    expect(screen.getByRole('complementary', { name: 'Symulacja' })).toHaveTextContent(
      'To nie jest prawdziwy alarm',
    )
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

describe('Page structure', () => {
  it('has a main landmark with a skip link to it', () => {
    render(<App demoMode={false} />)

    expect(screen.getByRole('main')).toHaveAttribute('id', 'main')
    expect(screen.getByRole('link', { name: 'Przejdź do treści' })).toHaveAttribute('href', '#main')
  })

  it('points aria-controls only at the rendered panel', () => {
    render(<App demoMode={false} />)

    expect(screen.getByRole('tab', { name: 'Zapytaj' })).toHaveAttribute(
      'aria-controls',
      'panel-chat',
    )
    expect(screen.getByRole('tab', { name: 'Mapa' })).not.toHaveAttribute('aria-controls')
    expect(document.getElementById('panel-chat')).toHaveAttribute('role', 'tabpanel')
  })
})

describe('Emergency bar', () => {
  it('keeps the other numbers in the DOM, hidden until expanded', async () => {
    render(<App demoMode={false} />)

    const toggle = screen.getByRole('button', { name: 'Inne numery' })
    const list = document.getElementById(toggle.getAttribute('aria-controls')!)
    expect(list).not.toBeNull()
    expect(list).not.toBeVisible()

    await userEvent.click(toggle)

    expect(list).toBeVisible()
  })

  it('always shows a callable 112 link', () => {
    render(<App demoMode={false} />)
    expect(screen.getByRole('link', { name: /112/ })).toHaveAttribute('href', 'tel:112')
  })
})
