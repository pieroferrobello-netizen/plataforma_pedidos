# MEMORY — Celia's Burger POS

Decisiones clave, contexto y estado del proyecto para no perder el hilo entre sesiones.

---

## Contexto del negocio
- Restaurante de pollo a la brasa / fast food en Perú.
- El sistema lo usa **giusseppe** (hermano, callcenter) para registrar pedidos por teléfono/WhatsApp.
- **piero** es el administrador (dueño).
- Acceso: red local — giusseppe entra desde su PC via `http://192.168.18.15:8501`.

## Decisiones técnicas
| Decisión | Por qué |
|---|---|
| Streamlit 1.54 como único tier | Simple de mantener, sin backend separado |
| Supabase (PostgreSQL) | Migrado desde Google Sheets el 2026-06-15 — más rápido, relacional, sin límite de filas |
| Font Awesome via CDN | Iconos reales en bloques HTML; tabs/botones de Streamlit usan emoji (limitación de plataforma) |
| Acceso por red local | No se necesita nube por ahora — la PC de piero siempre está encendida durante el turno |
| Expander labels: texto plano | `**markdown**` y backticks en labels de st.expander causan texto duplicado/superpuesto |
| st.html() para carrito | HTML con indentación Python en st.markdown() se interpreta como bloque de código Markdown |
| Pago mixto: formato pipe | `"Yape:25.00\|Efectivo:25.00"` — compatible con datos anteriores, parseable en Cierre de Caja |
| Alerta cierre de caja: horario fijo | Banner aparece 11 PM–1 AM (`hora >= 23 or hora < 1`), sin cambios en BD |
| Ticket de cocina: ESC/POS over TCP | `python-escpos` + `Network(PRINTER_IP, port=9100)`. `guardar_venta()` retorna `venta_id` (int truthy) o `None` (falsy). Ticket sin precios, agrupa cantidades con `Counter`. Si printer no conectada → warning, venta no se bloquea. |

## Base de datos Supabase
- **Proyecto**: `celias-burger` (`kiggakculokjznnxdkuk.supabase.co`)
- **Tablas**: `ventas`, `venta_items`, `productos`, `clientes`
- **Historial migrado**: 2.872 ventas + 6.864 ítems desde Google Sheets (Feb 2026 → Jun 2026)
- **Credenciales**: en `.streamlit/secrets.toml` (no subir a GitHub)

## Estado actual (2026-06-17)
- [x] Migración completa a Supabase
- [x] Panel admin de productos (solo piero)
- [x] Panel admin de clientes (solo piero)
- [x] Iconos Font Awesome, contador pedidos hoy, sonido al agregar, modo tablet
- [x] Anulación / edición de ventas (columna `anulada` en tabla `ventas`)
- [x] Fix labels de expanders (texto plano)
- [x] Fix íconos Material Symbols en expander (`[data-testid="stIconMaterial"]`)
- [x] Fix carrito HTML mostrándose como texto (migrado a `st.html()`)
- [x] Registrar venta en otra fecha/hora — toggle en Nueva Venta (ambos usuarios)
- [x] Pago mixto — toggle + inputs por método, desglose en Cierre de Caja
- [x] Login sin placeholders predeterminados
- [x] Alerta cierre de caja — banner rojo en todas las pantallas de 11 PM a 1 AM
- [x] Ticket de cocina — lógica implementada con python-escpos, pendiente conectar impresora (Xprinter XP-80CW WiFi)
- [ ] Configurar PRINTER_IP en app.py cuando la impresora esté en la red
- [ ] Subir a la nube (pendiente decisión)

## Reglas de desarrollo
- No tocar la lógica de negocio (carrito, cremas, acompañamientos) sin confirmación explícita.
- Actualizar este archivo y el README.md con cada cambio significativo.
- Verificar sintaxis con `python -m py_compile app.py` después de cada edición.
- Nunca usar markdown (`**`, backticks, `~~`) en labels de `st.expander`.
- El CSS `* { font-family: 'Outfit' !important }` rompe íconos de Streamlit 1.54 — siempre agregar override para `[data-testid="stIconMaterial"]` con `"Material Symbols Rounded"`.
- HTML con indentación Python no va en `st.markdown(unsafe_allow_html=True)` — usar `st.html()`.
- Pago mixto se guarda como `"Metodo1:monto|Metodo2:monto"` en columna `metodo`. El Cierre de Caja parsea el `|` para sumar por método.
