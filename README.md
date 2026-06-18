# Celia's Burger — Sistema POS

Sistema de punto de venta para registro de pedidos telefónicos y WhatsApp.

## Usuarios
| Usuario | Rol | Acceso |
|---|---|---|
| piero | Administrador | Nueva Venta, Cierre de Caja, Dashboard, Admin Productos, Admin Clientes, Gestionar Ventas |
| giusseppe | Cajero/Callcenter | Nueva Venta, Cierre de Caja, Gestionar Ventas |

## Tecnologías
- **Frontend/Backend**: Streamlit 1.54 (Python)
- **Base de datos**: Supabase (PostgreSQL)
- **Red**: Local — Giusseppe accede via `http://192.168.18.15:8501`

## Estructura de base de datos
```
ventas        → cabecera de cada pedido (fecha, cliente, total, método de pago, anulada)
venta_items   → detalle de productos por pedido (FK a ventas)
productos     → catálogo de productos con precio y categoría
clientes      → base de clientes con dirección y celular
```

## Funcionalidades completadas
- [x] Nueva Venta con carrito, cremas y acompañamientos
- [x] Cierre de Caja con movimientos del día y descarga Excel
- [x] Dashboard con métricas y gráficas históricas
- [x] Admin Productos — editar precios, activar/desactivar, agregar (solo piero)
- [x] Admin Clientes — editar, agregar y eliminar clientes (solo piero)
- [x] Gestionar Ventas — anular, reactivar y editar ventas del día
- [x] Registrar venta en otra fecha/hora — toggle en Nueva Venta (ambos usuarios)
- [x] Pago mixto — toggle para dividir el pago entre dos métodos (Yape + Efectivo, etc.)
- [x] Desglose por método en Cierre de Caja compatible con pagos mixtos
- [x] Alerta cierre de caja — banner rojo fijo en todas las pantallas de 11 PM a 1 AM
- [x] Login sin placeholders predeterminados
- [x] Migración histórica: 2.872 ventas + 6.864 ítems desde Google Sheets

## Formato de pago mixto en BD
- Pago simple: `"Efectivo"` / `"Yape"` / `"Tarjeta"`
- Pago mixto: `"Efectivo:25.00|Yape:25.00"` (pipe separa métodos, colon separa método:monto)
- El Cierre de Caja parsea ambos formatos automáticamente para el desglose

## Notas de UI
- Los expanders usan texto plano (sin `**` ni backticks) — evita texto duplicado en Streamlit 1.54.
- HTML del carrito usa `st.html()` — evita que la indentación Python se interprete como código Markdown.
- `[data-testid="stIconMaterial"]` necesita override `"Material Symbols Rounded"` — el CSS global `* { font-family: Outfit }` rompe los íconos de flecha.
- La alerta de cierre de caja aparece cuando `hora >= 23 or hora < 1` (11 PM – 1 AM).

## Cómo correr la app
```bash
streamlit run app.py
```

## Archivos sensibles (NO subir a GitHub)
- `.streamlit/secrets.toml` — credenciales Supabase
- Protegidos por `.gitignore`

## Ticket de cocina (impresora térmica)
- Modelo recomendado: **Xprinter XP-80CW** (WiFi, 80mm) — compra pendiente
- Librería: `python-escpos` (ya en `requirements.txt`)
- Configurar `PRINTER_IP` en `app.py` con la IP real de la impresora una vez en la red
- Puerto: 9100 (estándar ESC/POS over TCP)
- El ticket se envía automáticamente al confirmar la venta
- Contenido: nombre restaurante, # pedido, hora, cliente, tipo, dirección, teléfono y productos (sin precios)
- Si la impresora no está conectada, muestra un warning pero no bloquea la venta

## Pendientes / Roadmap
- [ ] Configurar IP de impresora (una vez conectada a la red WiFi)
- [ ] Subir a Streamlit Cloud para acceso sin depender de la PC local
