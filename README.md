# Celia's Burger — Sistema POS

Sistema de punto de venta (POS) desarrollado para un restaurante de comida rápida en Perú. Gestiona pedidos telefónicos y en mesa, cierre de caja diario y analítica de ventas en tiempo real.

## Demo

> Sistema en producción activa — usado diariamente para registrar y gestionar pedidos.

![Stack](https://img.shields.io/badge/Python-3.11-blue?logo=python) ![Streamlit](https://img.shields.io/badge/Streamlit-1.54-red?logo=streamlit) ![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green?logo=supabase)

---

## Funcionalidades

### 🛒 Nueva Venta
- Menú interactivo con 9 categorías de productos (broasters, hamburguesas, salchipapas, pizzas, etc.)
- Carrito en tiempo real con acompañamientos y cremas por producto
- Búsqueda de cliente por código o celular con autocompletado
- Soporte de pago mixto (ej: S/25 en Yape + S/25 en efectivo)
- Registro de ventas en fecha/hora alternativa

### 🏦 Cierre de Caja
- Resumen diario de ventas con desglose por método de pago
- Compatible con pagos mixtos (parsea formato `Yape:25.00|Efectivo:25.00`)
- Exportación a Excel (`.xlsx`)
- Filtro por fecha

### 📊 Dashboard Analítico
- KPIs: ingresos totales, pedidos, ticket promedio, horario punta
- Tendencia de ingresos diaria (gráfico de área)
- Demanda por bloques horarios (18 PM – 1 AM)
- Distribución por canal (mesa vs. call center)
- Top 5 clientes por monto
- Ranking de productos (mayor y menor ingreso)
- Desglose de ingresos por método de pago
- Filtros por fecha, canal, cliente y producto

### ⚙️ Administración
- Gestión de productos: precios, activar/desactivar, agregar
- Gestión de clientes: crear, editar, eliminar
- Anulación y edición de ventas del día
- Alerta automática de cierre de caja (11 PM – 1 AM)

### 🖨️ Ticket de Cocina *(en integración)*
- Impresión automática vía WiFi al confirmar pedido
- Formato ESC/POS con productos agrupados y acompañamientos
- Librería: `python-escpos`

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend / Backend | Streamlit 1.54 (Python) |
| Base de datos | Supabase (PostgreSQL) |
| Gráficos | Plotly Express + Graph Objects |
| Autenticación | Login con roles (admin / cajero) |
| Estilos | CSS custom + Font Awesome 6 + Outfit font |
| Impresora | python-escpos over TCP/WiFi |

---

## Arquitectura

```
app.py          → Lógica principal, navegación, vistas
dashboard.py    → Módulo analítico independiente
schema.sql      → Definición completa de la BD
requirements.txt
```

**Base de datos (Supabase / PostgreSQL):**
```
ventas        → Cabecera de cada pedido (fecha, cliente, total, método, anulada)
venta_items   → Detalle de productos por pedido (FK → ventas)
productos     → Catálogo con precio, categoría y estado activo
clientes      → Base de clientes con dirección y celular
```

**Historial migrado:** 2.872 ventas + 6.864 ítems desde Google Sheets (Feb – Jun 2026)

---

## Instalación local

```bash
git clone https://github.com/TU_USUARIO/celias-burger.git
cd celias-burger
pip install -r requirements.txt
```

Crea el archivo `.streamlit/secrets.toml` con tus credenciales de Supabase:
```toml
[supabase]
url = "https://tu-proyecto.supabase.co"
key = "tu-service-role-key"
```

```bash
streamlit run app.py
```

---

## Decisiones técnicas destacadas

- **Pago mixto** almacenado como `"Yape:25.00|Efectivo:25.00"` — compatible con datos históricos de pago simple, parseable en el cierre de caja.
- **`st.html()` para bloques HTML complejos** — evita que la indentación de Python sea interpretada como bloque de código Markdown.
- **Búsqueda de clientes sin caché** — consulta directa a Supabase con `ilike` para garantizar datos siempre frescos.
- **`@st.cache_data` con TTL diferenciado** — 300s para productos, 20s para ventas, sin caché en búsquedas puntuales.
- **Material Symbols override** — el CSS global `* { font-family: Outfit }` rompe los íconos internos de Streamlit 1.54; se restaura con selector específico `[data-testid="stIconMaterial"]`.
