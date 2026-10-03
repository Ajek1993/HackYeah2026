import type { ReactNode } from 'react'

// Minimal Markdown for agent answers: paragraphs, "-" / "*" lists, **bold**.
// Builds React nodes (no innerHTML), so model output can never inject markup.

function inline(text: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map((part, index) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={index}>{part.slice(2, -2)}</strong>
      ) : (
        part
      ),
    )
}

const BULLET = /^\s*[-*•]\s+/

export function RichText({ text }: { text: string }) {
  const blocks = text.trim().split(/\n\s*\n/)

  return (
    <div className="flex flex-col gap-3">
      {blocks.map((block, index) => {
        const lines = block.split('\n').filter((line) => line.trim())
        const bullets = lines.filter((line) => BULLET.test(line))
        const intro = lines.filter((line) => !BULLET.test(line))

        if (!bullets.length) {
          return <p key={index}>{inline(lines.join(' '))}</p>
        }
        return (
          <div key={index} className="flex flex-col gap-2">
            {intro.length > 0 && <p>{inline(intro.join(' '))}</p>}
            <ul className="flex list-disc flex-col gap-1 pl-6 marker:text-vistula">
              {bullets.map((line, item) => (
                <li key={item}>{inline(line.replace(BULLET, ''))}</li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
