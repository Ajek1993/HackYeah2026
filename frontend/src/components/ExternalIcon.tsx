/** Marks a link that leaves the app; pair it with NEW_TAB_HINT for screen readers. */
export function ExternalIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-5" aria-hidden="true" fill="none">
      <path
        d="M11 3h6v6M17 3l-8 8M8 5H4v11h11v-4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
