import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#102f6e',
          50: '#e8eef8',
          100: '#c5d4ef',
          200: '#9eb6e4',
          300: '#7797d9',
          400: '#5a81d0',
          500: '#3d6bc7',
          600: '#2d5ab0',
          700: '#1e4898',
          800: '#102f6e',
          900: '#0a1f4a',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
