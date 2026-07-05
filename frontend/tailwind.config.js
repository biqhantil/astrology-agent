/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Astrological element colors
        fire: '#ef4444',
        earth: '#22c55e',
        air: '#eab308',
        water: '#3b82f6',
        // Aspect colors
        conjunction: '#a855f7',
        sextile: '#22c55e',
        square: '#ef4444',
        trine: '#3b82f6',
        opposition: '#f97316',
        quincunx: '#a3a3a3',
        // UI theme
        surface: {
          DEFAULT: '#1e1b2e',
          light: '#2d2a3e',
          dark: '#13111d',
        },
        accent: {
          DEFAULT: '#c084fc',
          light: '#d8b4fe',
          dark: '#8b5cf6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        glyph: ['"AstroGlyphs"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
