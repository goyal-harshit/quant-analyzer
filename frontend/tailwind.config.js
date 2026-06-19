/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#030712",
        card: "#0a1020",
        elevated: "#0f182e",
        border: "#1e2d4a",
        borderHi: "#2a3f6a",
        brand: "#3b82f6",
        success: "#22c55e",
        danger: "#f43f5e",
        warn: "#f59e0b",
        purple: "#a78bfa",
        textPrimary: "#e2e8f0",
        textSub: "#94a3b8",
        textMuted: "#475569",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
