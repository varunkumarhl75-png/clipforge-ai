import type { Config } from 'tailwindcss';
const config: Config = { darkMode: 'class', content: ['./app/**/*.{js,ts,jsx,tsx,mdx}'], theme: { extend: { colors: { obsidian: '#07090E', 'luxury-panel': '#0D111A', champagne: '#F4B942' }, fontFamily: { display: ['Avenir Next', 'Segoe UI', 'sans-serif'] }, boxShadow: { luxury: '0 0 30px rgba(245,158,11,.28)' } } }, plugins: [] };
export default config;
