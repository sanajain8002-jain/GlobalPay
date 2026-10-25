/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gp: {
          obsidian: "#090714",
          surface: "#120E24",
          card: "#1B1534",
          electric: "#6D28D9",
          violet: "#8B5CF6",
          lavender: "#C4B5FD",
        },
      },
      fontFamily: {
        sans: ["Inter", "Manrope", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
