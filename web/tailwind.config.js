/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        terracotta: "#C75B39",
        "terracotta-dark": "#A8492B",
        ochre: "#D4A24C",
        "ochre-light": "#E8C886",
        forest: "#2D5A3D",
        "forest-dark": "#1F4129",
        "forest-light": "#3F7553",
        cream: "#FBF7F0",
        "cream-50": "#FDFBF6",
        "cream-100": "#F5EFE3",
        "cream-200": "#E8DFC8",
        "cream-300": "#D8CBA8",
        stone: "#6B7280",
        "stone-light": "#9CA3AF",
        ink: "#1F2937",
        "ink-soft": "#374151",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
};
