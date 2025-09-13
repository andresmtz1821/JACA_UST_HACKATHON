# Setup del Dashboard Moderno - La Huerta

## 🚀 Configuración Inicial

### 1. Instalar Dependencias
```bash
cd Layer6
npm install
```

### 2. Configurar Google Maps API

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Google Maps JavaScript
4. Crea credenciales (API Key)
5. Reemplaza `YOUR_API_KEY` en el archivo `views/dashboard.ejs` línea 12

### 3. Variables de Entorno

Crea un archivo `.env` con:
```env
PORT=3000
MQTT_BROKER=mqtt://localhost:1883
GOOGLE_MAPS_API_KEY=tu_clave_aqui
NODE_ENV=development
```

### 4. Compilar CSS
```bash
npm run build:css
```

### 5. Ejecutar el Dashboard
```bash
npm start
```

## 🎨 Características del Nuevo Diseño

### ✨ Tema Oscuro Moderno
- Fondo oscuro con efectos de glassmorphism
- Gradientes animados y efectos de brillo
- Paleta de colores específica para agricultura

### 🗺️ Mapa Satelital Interactivo
- Vista satelital de 15 invernaderos en Aguascalientes
- Marcadores con codificación por colores:
  - 🔴 **Rojo**: 15+ días para cosecha
  - 🟡 **Amarillo**: 8-14 días para cosecha  
  - 🟢 **Verde**: 1-7 días para cosecha

### 📊 Paneles Modernos
- **Anomalías**: Sistema de alertas con diferentes niveles de severidad
- **Días de Cosecha**: Contadores visuales por cada cosecha
- **Sensores**: Datos en tiempo real con efectos visuales
- **Recomendaciones IA**: Panel para análisis predictivo

### 🔧 Funcionalidades Técnicas
- WebSocket para actualizaciones en tiempo real
- Gráficos interactivos con Chart.js
- Efectos de sonido para alertas
- Responsive design para móvil y desktop

## 🎯 Próximos Pasos

1. **Obtener API Key de Google Maps** (requerido para el mapa)
2. **Conectar con el pipeline existente** (MQTT topics ya configurados)
3. **Personalizar coordenadas** de invernaderos según ubicación real
4. **Integrar modelo predictivo** del equipo

## 📱 Vista Previa

El dashboard incluye:
- Header con indicadores de estado del sistema
- Mapa satelital principal con invernaderos
- Panel lateral con métricas en tiempo real
- Sistema de alertas emergentes
- Gráficos de tendencias y progreso

## 🔗 Integración MQTT

Topics configurados:
- `invernadero/sensores/raw`
- `invernadero/anomalias` 
- `invernadero/alertas/emergentes`
- `invernadero/predicciones`

## 💡 Notas Importantes

- El mapa requiere conexión a internet para cargar
- Los datos de invernaderos son simulados para demo
- El sistema está preparado para integración con datos reales
- Compatible con el pipeline existente del proyecto

