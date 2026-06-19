// /frontend/lib/design-tokens.ts
export const tokens = {
  // SPACING — 4px base grid
  space: {
    1: '4px',   2: '8px',   3: '12px',  4: '16px',
    5: '20px',  6: '24px',  8: '32px',  10: '40px',
    12: '48px', 16: '64px', 20: '80px',
  },

  // PAGE LAYOUT
  layout: {
    sidebarExpanded: '224px',
    sidebarCollapsed: '64px',
    headerHeight: '64px',
    contentMaxWidth: '1440px',
    contentPadding: '32px',
    contentPaddingMobile: '16px',
    sectionGap: '32px',
    cardGap: '16px',
  },

  // TYPOGRAPHY SCALE
  font: {
    size: {
      xs: '11px',    // labels, timestamps
      sm: '12px',    // table cells
      base: '13px',  // body text
      md: '14px',    // card text
      lg: '15px',    // section text
      xl: '18px',    // card headings
      '2xl': '22px', // page sub-titles
      '3xl': '28px', // page titles
      '4xl': '36px', // hero numbers
    },
    weight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    mono: "'JetBrains Mono', 'Fira Code', monospace",
    sans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    display: "'Space Grotesk', 'Inter', sans-serif",
  },

  // BORDER RADIUS
  radius: {
    sm: '6px',   md: '8px',   lg: '12px',
    xl: '16px',  full: '9999px',
  },

  // Z-INDEX
  z: {
    sidebar: 40,   header: 50,
    modal: 100,    tooltip: 200,
    toast: 300,
  },
}
