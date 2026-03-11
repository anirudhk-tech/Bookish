/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg:      "#09090f",
        surface: "#111118",
        border:  "#1c1c28",
        muted:   "#2a2a3a",
        text:    "#e8e6e3",
        subtle:  "#6b6b80",
        accent:  "#f59e0b",
        tension: "#ef4444",
        calm:    "#3b82f6",
      },
      fontFamily: {
        serif: ["Playfair Display", "Georgia", "serif"],
        sans:  ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
