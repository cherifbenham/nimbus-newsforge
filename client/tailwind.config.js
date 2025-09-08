/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'customer-blue': '#C5D5F9'
      },
    },
  },
  plugins: ['@tailwindcss/forms', require('@tailwindcss/typography')],
}

