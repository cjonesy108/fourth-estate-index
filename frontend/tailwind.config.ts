import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-garamond)", "Georgia", "serif"],
        serif: ["var(--font-garamond)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Open Sans", "sans-serif"],
      },
      maxWidth: {
        page: "70rem",
      },
    },
  },
  plugins: [],
};

export default config;
