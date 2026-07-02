/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#080d18",
        card: "#0e1525",
        "card-hover": "#131d30",
        border: "#1a2540",
        accent: "#3b82f6",
        "accent-dim": "#1d4ed8",
        up: "#00c896",
        "up-bg": "rgba(0,200,150,0.10)",
        down: "#f43f5e",
        "down-bg": "rgba(244,63,94,0.10)",
        gold: "#f59e0b",
        muted: "#64748b",
        subtle: "#1e2d45",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 0 0 1px rgba(59,130,246,0.12), 0 4px 24px rgba(0,0,0,0.4)",
        "card-active": "0 0 0 1px rgba(59,130,246,0.5), 0 8px 32px rgba(59,130,246,0.15)",
        up: "0 0 12px rgba(0,200,150,0.25)",
        down: "0 0 12px rgba(244,63,94,0.25)",
      },
    },
  },
  plugins: [],
};
