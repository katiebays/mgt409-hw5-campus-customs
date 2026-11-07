/** Handsome Dan, drawn as a chubby bulldog in a bandana. Adapted from the course starter's mascot
 * (yale_som_courses_mcp). New here: eyes that open, paws that gallop, a prop, and a tennis ball in the mouth. */

export type DanMode = 'idle' | 'running' | 'working' | 'done' | 'blocked'

interface DanProps {
  fur: string
  bandana: string
  size?: number
  mode?: DanMode
  carry?: boolean
  prop?: string
}

function shade(hex: string, amt: number): string {
  const num = parseInt(hex.replace('#', ''), 16)
  const mixed = [(num >> 16) & 0xff, (num >> 8) & 0xff, num & 0xff].map((c) => {
    const target = amt >= 0 ? 255 : 0
    return Math.min(255, Math.max(0, Math.round(c + (target - c) * Math.abs(amt))))
  })
  return `#${mixed.map((v) => v.toString(16).padStart(2, '0')).join('')}`
}

export function TennisBall({ size = 26 }: { size?: number }) {
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden="true">
      <circle cx="20" cy="20" r="18" fill="#dff23d" stroke="#b9cc1c" strokeWidth="1.5" />
      <path d="M5 11 C 15 16, 15 24, 5 29" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M35 11 C 25 16, 25 24, 35 29" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

export default function Dan({ fur, bandana, size = 96, mode = 'idle', carry = false, prop }: DanProps) {
  const light = shade(fur, 0.4)
  const dark = shade(fur, -0.25)
  const bandanaDark = shade(bandana, -0.25)
  const ink = '#2b2320'
  const awake = mode === 'working' || mode === 'running'

  return (
    <div className={`dan ${mode}`} style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 120" width={size} height={size} className="dan-svg" aria-hidden="true">
        <ellipse cx="50" cy="102" rx="44" ry="30" fill={fur} />
        <ellipse className="paw paw-l" cx="29" cy="117" rx="10" ry="6" fill={light} />
        <ellipse className="paw paw-r" cx="71" cy="117" rx="10" ry="6" fill={light} />
        <path d="M13 27 q-4 17 10 27 q7 2 9 -5 q-4 -12 -3 -25 q-8 -4 -16 3 Z" fill={dark} />
        <path d="M87 27 q4 17 -10 27 q-7 2 -9 -5 q4 -12 3 -25 q8 -4 16 3 Z" fill={dark} />
        <ellipse cx="50" cy="42" rx="36" ry="27" fill={fur} />
        <ellipse cx="50" cy="57" rx="24" ry="14" fill={light} />
        <ellipse cx="32" cy="70" rx="14.5" ry="16.5" fill={light} />
        <ellipse cx="68" cy="70" rx="14.5" ry="16.5" fill={light} />
        <path d="M31 23 q19 -6 38 0" stroke={dark} strokeWidth="1.5" fill="none" opacity="0.4" strokeLinecap="round" />
        <path d="M29 31 q21 -5 42 0" stroke={dark} strokeWidth="1.5" fill="none" opacity="0.3" strokeLinecap="round" />

        {awake ? (
          <g>
            <ellipse cx="37" cy="35" rx="4.6" ry="5.4" fill={ink} />
            <ellipse cx="63" cy="35" rx="4.6" ry="5.4" fill={ink} />
            <circle cx="38.6" cy="33" r="1.5" fill="#fff" />
            <circle cx="64.6" cy="33" r="1.5" fill="#fff" />
          </g>
        ) : (
          <g>
            <path d="M32 36 q5 -7 10 0" stroke={ink} strokeWidth="2.5" fill="none" strokeLinecap="round" />
            <path d="M58 36 q5 -7 10 0" stroke={ink} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          </g>
        )}

        <ellipse cx="50" cy="51" rx="9.5" ry="6.5" fill={ink} />
        <ellipse cx="46.4" cy="51" rx="1.4" ry="2" fill="#000" opacity="0.55" />
        <ellipse cx="53.6" cy="51" rx="1.4" ry="2" fill="#000" opacity="0.55" />
        <path d="M50 57.5 v4.5" stroke={ink} strokeWidth="1.8" strokeLinecap="round" />
        <path d="M50 62 q-10 8 -18 3" stroke={ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />
        <path d="M50 62 q10 8 17 3" stroke={ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />
        {!carry && (
          <path d="M52.5 62 q4.5 10 -0.5 17 q-6 3 -8 -4 q-0.5 -8 8.5 -13 Z" fill="#e8899f" stroke="#c96a83" strokeWidth="0.6" />
        )}

        <path d="M24 80 L76 80 L50 106 Z" fill={bandana} stroke={bandanaDark} strokeWidth="1" />
        <path d="M24 80 q26 10 52 0" fill="none" stroke={bandanaDark} strokeWidth="1" opacity="0.55" />
        <text x="50" y="99" textAnchor="middle" fontFamily="Georgia, 'Libre Baskerville', serif" fontWeight={700} fontSize="14" fill="#ffffff">
          Y
        </text>

        {carry && (
          <g transform="translate(36 56)">
            <circle cx="14" cy="14" r="13" fill="#dff23d" stroke="#b9cc1c" strokeWidth="1.2" />
            <path d="M3 8 C 10 12, 10 18, 3 22" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M25 8 C 18 12, 18 18, 25 22" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
          </g>
        )}
      </svg>
      {prop && <span className="dan-prop">{prop}</span>}
      {mode === 'done' && <span className="dan-pip ok">✓</span>}
      {mode === 'blocked' && <span className="dan-pip bad">!</span>}
    </div>
  )
}
