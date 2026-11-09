/** @type {import('tailwindcss').Config} */

export default {
  content: [
    './app/**/*.{vue,js,ts,jsx,tsx}',
    './components/**/*.{vue,js,ts,jsx,tsx}',
    './layouts/**/*.{vue,js,ts,jsx,tsx}',
    './pages/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Terracotta — primary action, danger, deletion
        terracotta: {
          DEFAULT: '#C75B39',
          dark: '#A8492B',     // hover / pressed
          light: '#D6724F',    // softer hover
          soft: '#E89B7E',     // disabled-ish
          tint: '#F5DDD3',     // light bg
          wash: '#FAEAE5',     // lightest bg
        },
        // Ochre — accent, highlights, "nudge" banners
        ochre: {
          DEFAULT: '#D4A24C',
          dark: '#B8862E',     // print-safe / hover
          light: '#E8C886',
          tint: '#F5E8C8',
          wash: '#FAF0E0',
        },
        // Forest — brand, primary buttons, headings
        forest: {
          DEFAULT: '#2D5A3D',
          dark: '#1F4129',     // hover / pressed
          light: '#3F7553',
          soft: '#5A8B70',
          tint: '#E8F0EA',
          wash: '#F0F7F1',
        },
        // Cream — backgrounds, cards, borders
        cream: {
          DEFAULT: '#FBF7F0',
          50: '#FDFBF6',
          100: '#F5EFE3',
          200: '#E8DFC8',      // borders
          300: '#D8CBA8',
          400: '#C8B98A',
        },
        // Stone — secondary text, muted UI
        stone: {
          DEFAULT: '#6B7280',
          light: '#9CA3AF',
          dark: '#4B5563',
        },
        // Ink — primary text
        ink: {
          DEFAULT: '#1F2937',
          soft: '#374151',
          lighter: '#4B5563',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        // Soft shadows for cards / hover lift
        soft: '0 1px 2px 0 rgba(31, 41, 55, 0.04)',
        card: '0 2px 8px -2px rgba(31, 41, 55, 0.06), 0 1px 3px 0 rgba(31, 41, 55, 0.03)',
        lift: '0 6px 20px -4px rgba(31, 41, 55, 0.10), 0 2px 6px -2px rgba(31, 41, 55, 0.04)',
        ring: '0 0 0 3px rgba(45, 90, 61, 0.15)',
      },
      // Tighter type scale for the redesign
      fontSize: {
        '10': ['0.625rem', { lineHeight: '0.9rem' }],
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
        '6xl': ['3.75rem', { lineHeight: '1' }],
      },
    },
  },
  plugins: [],
}
