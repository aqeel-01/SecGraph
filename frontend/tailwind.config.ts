import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0b1020",
        panel: "#11182b",
        panel2: "#17213a",
        line: "#263452",
        muted: "#8b9ab8",
        cyan: "#5eead4",
        danger: "#fb7185",
        warning: "#fbbf24",
        info: "#60a5fa"
      },
      boxShadow: {
        glow: "0 0 40px rgba(94, 234, 212, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
