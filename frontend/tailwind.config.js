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
        // UI theme — pure black / zinc / cream / amber
        surface: {
          DEFAULT: '#0a0a0a',
          light: '#141414',
          dark: '#000000',
        },
        zinc: {
          DEFAULT: '#3f3f46',
          light: '#52525b',
          dark: '#27272a',
        },
        beige: {
          DEFAULT: '#d4c5a9',
          light: '#e8dcc8',
          dark: '#b8a88a',
        },
        accent: {
          DEFAULT: '#d97706',
          light: '#f59e0b',
          dark: '#b45309',
        },
        // Muted orange for subtle accents
        ember: {
          DEFAULT: '#ea580c',
          light: '#f97316',
          dark: '#c2410c',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        glyph: ['"AstroGlyphs"', 'sans-serif'],
      },
      animation: {
        'twinkle': 'twinkle 3s ease-in-out infinite',
        'twinkle-slow': 'twinkle 5s ease-in-out infinite',
        'drift': 'drift 20s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'fade-in': 'fadeIn 0.8s ease-out forwards',
        'slide-up': 'slideUp 0.8s ease-out forwards',
        'pulse-soft': 'pulseSoft 4s ease-in-out infinite',
      },
      keyframes: {
        twinkle: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.2)' },
        },
        drift: {
          '0%': { transform: 'translateY(0) translateX(0)' },
          '100%': { transform: 'translateY(-100vh) translateX(50px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(217,119,6,0.3), 0 0 20px rgba(217,119,6,0.1)' },
          '100%': { boxShadow: '0 0 10px rgba(217,119,6,0.5), 0 0 40px rgba(217,119,6,0.2)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
