import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#1A1A1A',
        cream: '#FAFAF7',
        teal: {
          DEFAULT: '#2A6F6F',
          soft: '#E6EFEF',
        },
        burgundy: {
          DEFAULT: '#8F1D3A',
          soft: '#F5E1E6',
        },
        slate: {
          border: '#3A3A3A',
          quote: '#F0EEE6',
        },
      },
      fontFamily: {
        serif: ['var(--font-source-serif)', 'Georgia', 'serif'],
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-ibm-plex-mono)', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        display: ['clamp(2rem, 4vw + 1rem, 3.5rem)', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        metric: ['clamp(2rem, 3vw + 1rem, 2.75rem)', { lineHeight: '1', letterSpacing: '-0.02em' }],
      },
      maxWidth: {
        prose: '68ch',
      },
    },
  },
  plugins: [],
};

export default config;
