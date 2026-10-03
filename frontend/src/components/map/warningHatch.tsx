// Diagonal hatch shared by the warning polygons and the legend swatch, so the legend
// matches the map and does not look like another checkbox. Absolute: no flex gap.
export const WARNING_HATCH = 'url(#warning-hatch)'

export function WarningHatchDefs() {
  return (
    <svg aria-hidden="true" className="absolute size-0">
      <defs>
        <pattern
          id="warning-hatch"
          width="8"
          height="8"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="8" height="8" fill="#b42318" fillOpacity="0.1" />
          <rect width="3" height="8" fill="#b42318" fillOpacity="0.45" />
        </pattern>
      </defs>
    </svg>
  )
}
