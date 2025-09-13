/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.html",
    "./public/**/*.js",
    "./views/**/*.ejs",
    "./src/**/*.js"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Paleta oscura moderna para agricultura
        'dark': {
          '50': '#f8fafc',
          '100': '#f1f5f9',
          '200': '#e2e8f0',
          '300': '#cbd5e1',
          '400': '#94a3b8',
          '500': '#64748b',
          '600': '#475569',
          '700': '#334155',
          '800': '#1e293b',
          '900': '#0f172a',
          '950': '#020617'
        },
        // Colores para agricultura de precisión
        'greenhouse': {
          '50': '#f0fdf4',
          '100': '#dcfce7',
          '200': '#bbf7d0',
          '300': '#86efac',
          '400': '#4ade80',
          '500': '#22c55e',
          '600': '#16a34a',
          '700': '#15803d',
          '800': '#166534',
          '900': '#14532d'
        },
        // Estados de cosecha
        'harvest': {
          'early': '#ef4444',    // Rojo - muchos días restantes
          'mid': '#f59e0b',      // Amarillo - días medios
          'ready': '#22c55e'     // Verde - pocos días restantes
        },
        // Anomalías y alertas
        'anomaly': {
          'critical': '#dc2626',
          'high': '#ea580c',
          'medium': '#d97706',
          'low': '#65a30d'
        },
        // Acentos modernos
        'accent': {
          'cyan': '#06b6d4',
          'purple': '#8b5cf6',
          'pink': '#ec4899',
          'emerald': '#10b981'
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s infinite',
        'bounce-subtle': 'bounce 2s infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'gradient': 'gradient 3s ease infinite'
      },
      keyframes: {
        glow: {
          'from': { boxShadow: '0 0 5px rgba(34, 197, 94, 0.5)' },
          'to': { boxShadow: '0 0 20px rgba(34, 197, 94, 0.8)' }
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' }
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' }
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'dark-pattern': 'linear-gradient(45deg, #0f172a 25%, transparent 25%), linear-gradient(-45deg, #0f172a 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #0f172a 75%), linear-gradient(-45deg, transparent 75%, #0f172a 75%)'
      },
      backdropBlur: {
        'xs': '2px',
      }
    },
  },
  plugins: [],
}