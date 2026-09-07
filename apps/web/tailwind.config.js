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
        },
        ocean: {
          950: '#020617',
          900: '#0b132b',
          800: '#1c2541',
          700: '#3a506b',
        }
      },
      fontFamily: {
        amita: ['Amita', 'cursive'],
        cinzel: ['Cinzel', 'serif'],
        heading: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
