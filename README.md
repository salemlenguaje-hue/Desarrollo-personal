# 📚 Diario de Capacitación y Desarrollo Académico

Sistema personal de registro de estudio con:
- 🔥 Rachas y niveles estilo juego (metas de 7 a 365 días)
- 🔐 Blockchain personal: cada entrada lleva hash, hash previo y firma
- 📊 Página de análisis con gráficos y calendario de actividad
- 📤 Compilado diario compartible por GitHub, email o WhatsApp
- 🖨️ Reporte imprimible / guardable como PDF
- 📦 Backups en Zip hacia la carpeta Download de Android

## 🚀 Cómo usarlo

```bash
./iniciar.sh          # enciende el servidor en el puerto 2527
python backup.py      # genera un Zip de respaldo en Download
```

Después entrá desde el navegador a: http://localhost:2527

## 🗂️ Estructura

- `server.py` — servidor web (Flask)
- `logica.py` — cerebro: rachas, niveles, blockchain, compilados
- `templates/` — pantallas HTML
- `static/` — logo, estilos y scripts
- `compilados/` — actas diarias en Markdown

Hecho con ❤️ en Termux, Android y Python.
