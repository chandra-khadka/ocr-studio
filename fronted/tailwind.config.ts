import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        primary: '#00A651',
        'primary-dark': '#008c44',
        'primary-light': '#e7faee',
        secondary: '#385242',
        accent: '#4CAF50'
      },
      boxShadow: {
        hero: '0 8px 32px rgba(60,160,100,0.08)',
        card: '0 6px 24px rgba(60,160,100,0.08)'
      },
      borderRadius: {
        '2xl': '1.25rem'
      }
    },
  },
  plugins: [],
} satisfies Config
