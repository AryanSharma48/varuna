/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#2563eb',
          'blue-hover': '#1d4ed8',
          'blue-light': '#3b82f6',
          'blue-dim': 'rgba(37, 99, 235, 0.1)',
        }
      },
      fontFamily: {
        sans: ['Geist', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'monospace'],
      },
      borderRadius: {
        none: '0px',
        DEFAULT: '0px',
      }
    },
  },
  plugins: [],
}
