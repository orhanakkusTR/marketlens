/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Binance dark tema (CLAUDE.md tasarım sistemi)
        binance: {
          bg: '#0B0E11',
          surface: '#1E2329',
          border: '#2B3139',
          long: '#0ECB81',
          short: '#F6465D',
          neutral: '#848E9C',
          accent: '#F0B90B',
          text: {
            primary: '#EAECEF',
            secondary: '#B7BDC6',
            muted: '#848E9C',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        // CLAUDE.md: kart için rounded-lg, diğer için rounded-md
        DEFAULT: '0.375rem',
      },
    },
  },
  plugins: [],
}
