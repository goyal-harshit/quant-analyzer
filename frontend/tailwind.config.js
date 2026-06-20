/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:           'var(--bg)',
        card:         'var(--card)',
        elevated:     'var(--elevated)',
        border:       'var(--border)',
        borderHi:     'var(--border-hi)',
        brand:        'var(--brand)',
        success:      'var(--success)',
        danger:       'var(--danger)',
        warn:         'var(--warn)',
        purple:       'var(--purple)',
        cyan:         'var(--cyan)',
        textPrimary:  'var(--text-primary)',
        textSub:      'var(--text-sub)',
        textMuted:    'var(--text-muted)',
      },
      fontFamily: {
        sans:    ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Space Grotesk', 'Inter', 'sans-serif'],
      },
      fontSize: {
        'xs':   ['11px', { lineHeight: '16px' }],
        'sm':   ['12px', { lineHeight: '18px' }],
        'base': ['13px', { lineHeight: '20px' }],
        'md':   ['14px', { lineHeight: '22px' }],
        'lg':   ['15px', { lineHeight: '24px' }],
        'xl':   ['18px', { lineHeight: '28px' }],
        '2xl':  ['22px', { lineHeight: '32px', letterSpacing: '-0.01em' }],
        '3xl':  ['28px', { lineHeight: '36px', letterSpacing: '-0.02em' }],
        '4xl':  ['36px', { lineHeight: '44px', letterSpacing: '-0.03em' }],
      },
      spacing: {
        '0.5': '2px', '1': '4px',  '1.5': '6px',  '2': '8px',
        '2.5': '10px','3': '12px', '3.5': '14px', '4': '16px',
        '5': '20px',  '6': '24px', '7': '28px',   '8': '32px',
        '9': '36px',  '10': '40px','12': '48px',  '14': '56px',
        '16': '64px', '20': '80px','24': '96px',  '28': '112px',
        '32': '128px',
      },
      borderRadius: {
        'sm': '6px', DEFAULT: '8px', 'md': '8px',
        'lg': '12px','xl': '16px',  '2xl': '20px', 'full': '9999px',
      },
      boxShadow: {
        'card':  '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'panel': '0 4px 12px rgba(0,0,0,0.5)',
        'none':  'none',
      },
    },
  },
  plugins: [],
}
