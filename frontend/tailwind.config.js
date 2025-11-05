/** @type {import('tailwindcss').Config} */
module.exports = {
  content: {
    files: [
      './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    extract: {
      // Only extract from actual component files, not markdown or python files
      include: ['**/*.{js,jsx,ts,tsx}'],
      exclude: [
        '**/node_modules/**',
        '**/agents/**',
        '**/combatpower/**',
        '**/esports-mcp/**',
        '**/*.md',
        '**/*.py',
      ],
    },
  },
  theme: {
    extend: {},
  },
  plugins: [],
}
