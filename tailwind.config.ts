import type { Config } from "tailwindcss";

// Design tokens per CLAUDE.md §14. Values below are PLACEHOLDERS —
// [FILL]: replace each with the exact value from thelearnerlab.com theme CSS.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: "#faf6ec", // [FILL] page background
        ink: "#1c1b18", // [FILL] text, strokes
        "ink-muted": "#6f6a5e", // [FILL] secondary text, rules
        yellow: "#f5c518", // [FILL] the one accent
        rule: "#e3dcc9", // [FILL] hairlines
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["'Libre Franklin'", "system-ui", "sans-serif"],
        hand: ["Caveat", "cursive"],
      },
    },
  },
  plugins: [],
};

export default config;
