#!/data/data/com.termux/files/usr/bin/bash

# Limpiamos la pantalla para que se vea prolijo
clear

# Nos aseguramos de estar en la carpeta correcta
cd ~/Desarrollo-personal

echo "=================================================="
echo "  📚 DIARIO DE CAPACITACIÓN Y DESARROLLO ACADÉMICO"
echo "=================================================="
echo ""
echo "🚀 Encendiendo servidores en puerto 2527..."
echo "🔗 Entrá desde tu celu en: http://localhost:2527"
echo "🔗 Entrá desde la WiFi en: http://$(ip route get 1.1.1.1 | awk '{print $7}'):2527"
echo ""
echo "⚠️  Para apagar el servidor presioná: Ctrl + C"
echo "--------------------------------------------------"

# Arrancamos el servidor de Python
python server.py
