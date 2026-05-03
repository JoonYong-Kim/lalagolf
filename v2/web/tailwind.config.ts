import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f7f8f6",
        ink: "#202420",
        muted: "#687068",
        line: "#dfe4dd",
        green: {
          700: "#1f5f3c",
          800: "#17482e"
        }
      }
    }
  },
  plugins: []
};

export default config;
