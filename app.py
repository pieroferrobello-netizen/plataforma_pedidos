import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import os
import dashboard
from collections import Counter

# ── CONFIG IMPRESORA TÉRMICA ─────────────────────────────
PRINTER_IP   = "192.168.18.XXX"   # ← cambiar a la IP real de la XP-80CW una vez configurada
PRINTER_PORT = 9100

try:
    from escpos.printer import Network as _EscposNetwork
    _ESCPOS_OK = True
except ImportError:
    _ESCPOS_OK = False

st.set_page_config(
    page_title="Celia's Burger — POS",
    layout="wide",
    page_icon="🍔",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════
#  JS: forzar sidebar siempre visible
# ═══════════════════════════════════════════════════════
components.html("""
<script>
var NAV_ICONS = {
    'Nueva Venta':     'fa-cash-register',
    'Cierre de Caja':  'fa-vault',
    'Dashboard':       'fa-chart-line',
    'Admin Productos': 'fa-box-open',
    'Admin Clientes':  'fa-users',
    'Gestionar Ventas':'fa-pen-to-square'
};
function injectNavIcons() {
    try {
        var doc = window.parent.document;
        var ps = doc.querySelectorAll('[data-testid="stSidebar"] .stRadio p');
        ps.forEach(function(p) {
            var txt = p.innerText.trim();
            if (NAV_ICONS[txt] && !p.querySelector('i')) {
                var ic = doc.createElement('i');
                ic.className = 'fa-solid ' + NAV_ICONS[txt];
                ic.style.cssText = 'margin-right:10px;width:16px;text-align:center;flex-shrink:0;font-size:13px;';
                p.insertBefore(ic, p.firstChild);
            }
        });
    } catch(e) {}
}
function lockSidebar() {
    try {
        var doc = window.parent.document;
        var sb = doc.querySelector('[data-testid="stSidebar"]');
        if (sb) {
            sb.style.setProperty('transform',   'translateX(0)',  'important');
            sb.style.setProperty('visibility',  'visible',        'important');
            sb.style.setProperty('display',     'flex',           'important');
            sb.style.setProperty('min-width',   '252px',          'important');
        }
        doc.querySelectorAll('[data-testid="collapsedControl"]').forEach(
            function(e){ e.style.setProperty('display','none','important'); }
        );
        doc.querySelectorAll('[data-testid="stSidebarCollapseButton"]').forEach(
            function(e){ e.style.setProperty('display','none','important'); }
        );
    } catch(e) {}
}
lockSidebar();
injectNavIcons();
setInterval(function(){ lockSidebar(); injectNavIcons(); }, 300);
</script>
""", height=0, scrolling=False)

# ═══════════════════════════════════════════════════════
#  CSS GLOBAL
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');
* { font-family: 'Outfit', sans-serif !important; }
/* Restaurar fuente Material Symbols para íconos de Streamlit (expander arrow, etc.) */
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded" !important;
}
/* Restaurar Font Awesome en elementos <i> con clases FA */
i.fa-solid, i.fa-regular, i.fa-brands, i[class*="fa-"] {
    font-family: "Font Awesome 6 Free", "Font Awesome 6 Brands" !important;
}
i.fa-solid { font-weight: 900 !important; }
i.fa-regular { font-weight: 400 !important; }
i.fa-brands { font-family: "Font Awesome 6 Brands" !important; font-weight: 400 !important; }

/* Ocultar chrome Streamlit */
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none !important; }
header[data-testid="stHeader"]    { display: none !important; }
[data-testid="stToolbar"]          { display: none !important; }
[data-testid="collapsedControl"]   { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[title="Close sidebar"]      { display: none !important; }
button[title="Open sidebar"]       { display: none !important; }

/* Fondo */
.stApp { background: #080b10; }

/* ════ SIDEBAR SIEMPRE VISIBLE ════ */
section[data-testid="stSidebar"] {
    transform: translateX(0) !important;
    visibility: visible !important;
    display: flex !important;
    background: #0a0d13 !important;
    border-right: 1px solid #1c2128 !important;
    min-width: 252px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* Nav radio — quitar círculos y label "nav", estilizar como pills */
section[data-testid="stSidebar"] .stRadio > div { gap: 3px !important; }
/* Ocultar el círculo visual del radio */
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label > div:first-child { display: none !important; }
/* Ocultar label del radio ("nav") */
section[data-testid="stSidebar"] .stRadio > label { display: none !important; }
section[data-testid="stSidebar"] .stRadio input[type="radio"] { display: none !important; }
section[data-testid="stSidebar"] .stRadio p { font-size: 14px !important; font-weight: 600 !important; display: flex !important; align-items: center !important; margin: 0 !important; }
section[data-testid="stSidebar"] .stRadio label {
    display: flex !important;
    align-items: center !important;
    padding: 11px 16px !important;
    border-radius: 10px !important;
    cursor: pointer !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #6e7681 !important;
    transition: all 0.15s !important;
    margin: 1px 0 !important;
    border: 1px solid transparent !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: #161b22 !important;
    color: #e6edf3 !important;
    border-color: #21262d !important;
}
section[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: #161b22 !important;
    color: #ffffff !important;
    border: 1px solid #21262d !important;
    border-left: 3px solid #E63946 !important;
    padding-left: 14px !important;
}

/* Botón cerrar sesión (sidebar) */
section[data-testid="stSidebar"] div.stButton > button {
    background: transparent !important;
    border: 1px solid #21262d !important;
    color: #6e7681 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    min-height: 38px !important;
    box-shadow: none !important;
    transform: none !important;
}
section[data-testid="stSidebar"] div.stButton > button:hover {
    background: #161b22 !important;
    border-color: #E63946 !important;
    color: #E63946 !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ════ TABS ════ */
.stTabs [data-baseweb="tab-list"] {
    background: #0a0d13;
    border-radius: 16px;
    padding: 5px;
    gap: 3px;
    border: 1px solid #1c2128;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 12px;
    color: #484f58 !important;
    font-weight: 800;
    font-size: 11px;
    padding: 9px 14px;
    letter-spacing: 0.8px;
    white-space: nowrap;
    text-transform: uppercase;
    transition: color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover { color: #8b949e !important; }
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #E63946, #a50d1a) !important;
    color: white !important;
    box-shadow: 0 4px 16px rgba(230,57,70,0.5);
    letter-spacing: 1px;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"]    { display: none; }

/* ════ BOTONES PRODUCTO (área principal) ════ */
.main div.stButton > button {
    background: linear-gradient(160deg, #13181f 0%, #080b10 100%) !important;
    border: 1px solid #21262d !important;
    border-bottom: 3px solid #E63946 !important;
    color: #c9d1d9 !important;
    border-radius: 14px !important;
    font-weight: 900 !important;
    font-size: 12px !important;
    min-height: 84px !important;
    padding: 12px 10px !important;
    transition: all 0.2s cubic-bezier(.4,0,.2,1) !important;
    white-space: pre-line !important;
    line-height: 1.8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    position: relative !important;
}
.main div.stButton > button:hover {
    background: linear-gradient(160deg, #E63946 0%, #7d0610 100%) !important;
    border-color: #E63946 !important;
    border-bottom-color: rgba(0,0,0,0.3) !important;
    color: white !important;
    box-shadow: 0 14px 40px rgba(230,57,70,0.65), 0 0 0 1px #E63946 !important;
    transform: translateY(-5px) scale(1.03) !important;
}
.main div.stButton > button:active {
    transform: translateY(-1px) scale(0.99) !important;
    box-shadow: 0 4px 12px rgba(230,57,70,0.4) !important;
}

/* Botón CONFIRMAR VENTA */
.main div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #E63946 0%, #7d0610 100%) !important;
    border: none !important;
    border-bottom: 3px solid rgba(0,0,0,0.3) !important;
    color: white !important;
    font-size: 15px !important;
    font-weight: 900 !important;
    min-height: 56px !important;
    letter-spacing: 2px;
    box-shadow: 0 8px 28px rgba(230,57,70,0.55), inset 0 1px 0 rgba(255,255,255,0.15) !important;
    text-transform: uppercase !important;
}
.main div.stButton > button[kind="primary"]:hover {
    box-shadow: 0 14px 40px rgba(230,57,70,0.75) !important;
    transform: translateY(-2px) !important;
}

/* ════ CONTENEDORES ════ */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #0d1117 !important;
    border: 1px solid #1c2128 !important;
    border-radius: 18px !important;
}

/* ════ MÉTRICAS ════ */
div[data-testid="metric-container"] {
    background: #0d1117;
    border: 1px solid #1c2128;
    border-radius: 16px;
    padding: 22px 26px !important;
}
div[data-testid="stMetricValue"] {
    font-size: 2.4rem !important;
    font-weight: 900 !important;
    color: #E63946 !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    color: #484f58 !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ════ INPUTS ════ */
.stTextInput input {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    color: #e6edf3 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}
.stTextInput input:focus {
    border-color: #E63946 !important;
    box-shadow: 0 0 0 3px rgba(230,57,70,0.2) !important;
}

/* ════ SELECTBOX ════ */
.stSelectbox > div > div {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    color: #e6edf3 !important;
}

/* ════ CHECKBOXES ════ */
.stCheckbox label {
    font-size: 13px !important;
    color: #c9d1d9 !important;
    font-weight: 500 !important;
}

/* ════ DIVISORES ════ */
hr { border-color: #1c2128 !important; margin: 10px 0 !important; }

/* ════ DATAFRAME ════ */
.stDataFrame th {
    background: #0d1117 !important;
    color: #484f58 !important;
    font-size: 10px !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
#  USUARIOS
# ═══════════════════════════════════════════════════════
USUARIOS = {"piero": "admin123", "giusseppe": "caja1"}

if 'logueado' not in st.session_state:
    st.session_state['logueado'] = False

def login():
    st.markdown("<div style='height:70px'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 0.9, 1])
    with col:
        # Marca sin logo
        st.markdown("""
        <div style='text-align:center; margin-bottom:36px;'>
            <div style='font-size:42px; font-weight:900; color:#E63946;
                        letter-spacing:-1.5px; line-height:1;'>CELIA'S</div>
            <div style='font-size:11px; font-weight:800; color:#6e7681;
                        letter-spacing:6px; text-transform:uppercase; margin-top:6px;'>
                BURGER · POS
            </div>
            <div style='width:48px; height:3px; background:linear-gradient(90deg,#E63946,#c1121f);
                        margin:14px auto 0; border-radius:3px;'></div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
            <p style='font-size:17px; font-weight:800; color:#e6edf3; margin:0 0 2px;'>
                Iniciar sesión
            </p>
            <p style='font-size:12px; color:#484f58; margin:0 0 18px;'>
                Solo personal autorizado
            </p>
            """, unsafe_allow_html=True)
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.button("Ingresar", type="primary", use_container_width=True):
                if u in USUARIOS and USUARIOS[u] == p:
                    st.session_state['logueado'] = True
                    st.session_state['usuario_actual'] = u
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")

if not st.session_state['logueado']:
    login()
    st.stop()

def logout():
    st.session_state['logueado'] = False
    st.rerun()

# ═══════════════════════════════════════════════════════
#  SUPABASE
# ═══════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

@st.cache_data(ttl=30)
def cargar_datos_supabase():
    try:
        sb = get_supabase()
        prod_rows = sb.table("productos").select("*").eq("activo", True).execute().data
        cli_rows  = sb.table("clientes").select("*").execute().data
        prod = pd.DataFrame(prod_rows)
        cli  = pd.DataFrame(cli_rows)
        prod = prod.rename(columns={"codigo": "CODIGO", "nombre": "PRODUCTO",
                                    "precio": "PRECIO", "categoria": "Categoria_Auto"})
        prod['CODIGO'] = prod['CODIGO'].astype(str)
        cli  = cli.rename(columns={"codigo": "CODIGO", "nombre": "CLIENTE",
                                   "direccion": "DIRECCION", "celular": "CELULAR"})
        cli['CODIGO'] = cli['CODIGO'].astype(str)
        cli['CELULAR'] = cli['CELULAR'].fillna('').astype(str)
        return prod, cli
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

def _paginar(tabla, columnas="*", filtros=None):
    """Lee todas las filas de una tabla Supabase paginando de a 1000."""
    sb   = get_supabase()
    rows = []
    off  = 0
    while True:
        q = sb.table(tabla).select(columnas)
        if filtros:
            for col, val in filtros.items():
                q = q.gte(col, val) if isinstance(val, tuple) else q.eq(col, val)
        batch = q.order("id").range(off, off + 999).execute().data
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        off += 1000
    return rows

@st.cache_data(ttl=20)
def obtener_datos_ventas():
    try:
        sb  = get_supabase()
        # Cargar ventas DESC por fecha → los más recientes llegan en la página 1
        ventas, off = [], 0
        while True:
            batch = (sb.table("ventas").select("*")
                       .order("fecha", desc=True)
                       .range(off, off + 999)
                       .execute().data)
            if not batch:
                break
            ventas.extend(batch)
            if len(batch) < 1000:
                break
            off += 1000

        if not ventas:
            return pd.DataFrame()
        df = pd.DataFrame(ventas)
        if "anulada" in df.columns:
            df = df[df["anulada"] != True]

        items_rows = _paginar("venta_items", "venta_id, producto")
        if items_rows:
            items_df      = pd.DataFrame(items_rows)
            items_grouped = items_df.groupby("venta_id")["producto"].apply(lambda x: ", ".join(x)).reset_index()
            items_grouped.columns = ["id", "Items"]
            df = df.merge(items_grouped, on="id", how="left")
        else:
            df["Items"] = ""
        df = df.rename(columns={
            "fecha": "Fecha", "usuario": "Usuario", "cliente": "Cliente",
            "tipo": "Tipo", "total": "Total", "metodo": "Pago",
            "direccion": "Direccion", "celular": "Celular",
        })
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=20)
def contar_pedidos_hoy():
    try:
        sb  = get_supabase()
        hoy = datetime.now().strftime("%Y-%m-%d")
        res = sb.table("ventas").select("id", count="exact").gte("fecha", hoy + "T00:00:00").lte("fecha", hoy + "T23:59:59").execute()
        return res.count or 0
    except:
        return 0

def guardar_venta(usuario, cliente, tipo, total, direccion, celular, metodo, items, fecha_override=None):
    try:
        sb = get_supabase()
        fecha = fecha_override if fecha_override else datetime.now().isoformat()
        venta = sb.table("ventas").insert({
            "fecha":     fecha,
            "usuario":   usuario,
            "cliente":   cliente,
            "tipo":      tipo,
            "total":     total,
            "direccion": direccion,
            "celular":   celular,
            "metodo":    metodo,
        }).execute().data[0]
        venta_id = venta["id"]
        item_rows = [{"venta_id": venta_id, "producto": it["Producto"],
                      "precio": it["Precio"]} for it in items]
        sb.table("venta_items").insert(item_rows).execute()
        return venta_id
    except Exception as e:
        st.error(f"Error guardando venta: {e}")
        return None


def imprimir_ticket_cocina(venta_id, cliente, tipo, items, direccion="", celular=""):
    """Envía ticket de cocina a la impresora térmica via WiFi. Retorna True o mensaje de error."""
    if not _ESCPOS_OK:
        return "python-escpos no instalado — ejecuta: pip install python-escpos"
    if "XXX" in PRINTER_IP:
        return "IP de impresora no configurada (edita PRINTER_IP en app.py)"
    try:
        conteo = Counter(it["Producto"] for it in items)
        p = _EscposNetwork(PRINTER_IP, port=PRINTER_PORT, timeout=3)
        SEP = "=" * 42
        sep = "-" * 42
        hora = datetime.now().strftime("%I:%M %p")

        p.set(align='center', bold=True, double_height=True)
        p.text("CELIA'S BURGER\n")
        p.set(align='center', bold=True, double_height=False)
        p.text("C O C I N A\n")
        p.set(bold=False)
        p.text(SEP + "\n")

        p.set(align='left')
        p.text(f" Pedido #{venta_id}    {hora}\n")
        p.text(sep + "\n")

        p.set(bold=True)
        p.text(f" {cliente.upper()}\n")
        p.set(bold=False)
        p.text(f" Tipo: {tipo.upper()}\n")
        if celular:
            p.text(f" Tel:  {celular}\n")
        if direccion:
            dir_str = str(direccion)
            p.text(f" Dir:  {dir_str[:36]}\n")
            if len(dir_str) > 36:
                p.text(f"       {dir_str[36:72]}\n")
        p.text(SEP + "\n")

        p.set(bold=True)
        for producto, qty in conteo.items():
            prefijo = f" {qty}x "
            linea   = prefijo + producto
            if len(linea) <= 42:
                p.text(linea + "\n")
            else:
                # primera línea con prefijo, resto indentado
                p.text(linea[:42] + "\n")
                resto = linea[42:]
                while resto:
                    p.text("    " + resto[:38] + "\n")
                    resto = resto[38:]

        p.set(bold=False)
        p.text(SEP + "\n")
        p.set(align='center')
        p.text("\n\n\n")
        p.cut()
        p.close()
        return True
    except Exception as e:
        return str(e)


df_productos, df_clientes = cargar_datos_supabase()

# ═══════════════════════════════════════════════════════
#  CARRITO
# ═══════════════════════════════════════════════════════
if 'pedido' not in st.session_state:
    st.session_state.pedido = []

def agregar_item(producto, precio):
    st.session_state.pedido.append({"Producto": producto, "Precio": precio})
    st.session_state.just_added = True
    st.toast(f"✅  {producto}")

def eliminar_ultimo():
    if st.session_state.pedido:
        st.session_state.pedido.pop()
        st.rerun()

# Sonido/vibración al agregar producto
if st.session_state.get('just_added'):
    st.session_state.just_added = False
    components.html("""
    <script>
    try {
        var ctx = new (window.parent.AudioContext || window.parent.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
        osc.start(); osc.stop(ctx.currentTime + 0.18);
        if (window.parent.navigator.vibrate) { window.parent.navigator.vibrate(60); }
    } catch(e) {}
    </script>
    """, height=0, scrolling=False)

# ═══════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════
CAT_META = {
    'BROASTERS':    ('#E63946', '#7d0610', 'fa-fire'),
    'HAMBURGUESAS': ('#E67E22', '#7a3800', 'fa-burger'),
    'SALCHIPAPAS':  ('#c9a500', '#6b5000', 'fa-hotdog'),
    'PIZZAS':       ('#c0392b', '#6b1510', 'fa-pizza-slice'),
    'CARTA':        ('#1a9e58', '#0a4f2b', 'fa-utensils'),
    'GASEOSAS':     ('#1a7ec0', '#0a3d6b', 'fa-bottle-water'),
    'REFRESCOS':    ('#8E44AD', '#451060', 'fa-martini-glass-citrus'),
    'INFUSIONES':   ('#c05a00', '#5e2800', 'fa-mug-hot'),
    'EXTRAS':       ('#3d4f5c', '#1a252b', 'fa-star'),
}

# ═══════════════════════════════════════════════════════
#  ALERTA CIERRE DE CAJA (11 PM – 1 AM)
# ═══════════════════════════════════════════════════════
_hora_actual = datetime.now().hour
if _hora_actual >= 23 or _hora_actual < 1:
    st.markdown("""
<div style='
    background: linear-gradient(135deg, #7d0610 0%, #E63946 100%);
    border: 1px solid #ff6b6b;
    border-radius: 14px;
    padding: 16px 22px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    box-shadow: 0 4px 24px rgba(230,57,70,0.4);
'>
    <div style='display:flex; align-items:center; gap:14px;'>
        <span style='font-size:28px;'>🔔</span>
        <div>
            <div style='font-size:14px; font-weight:900; color:white; letter-spacing:0.5px;'>
                ¡CIERRE DE CAJA PENDIENTE!
            </div>
            <div style='font-size:12px; color:rgba(255,255,255,0.8); margin-top:2px;'>
                Recuerda registrar el cierre del día antes de la 1:00 AM.
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    usuario = st.session_state['usuario_actual']
    rol     = "Administrador" if usuario == "piero" else "Cajero"
    icono   = "fa-crown" if usuario == "piero" else "fa-user-tie"

    # Brand header sidebar
    if os.path.exists("logo.png"):
        _, lc, _ = st.columns([0.5, 2, 0.5])
        with lc:
            st.image("logo.png", width=115)
    st.markdown("""
    <div style='text-align:center; padding:4px 0 16px; border-bottom:1px solid #1c2128;
                margin-bottom:4px;'>
        <div style='font-size:11px; font-weight:800; color:#484f58;
                    letter-spacing:4px; text-transform:uppercase;'>
            <i class='fa-solid fa-microchip' style='margin-right:6px;'></i>SISTEMA POS
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Card usuario
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#13181f,#0a0d13);
                border:1px solid #1c2128; border-radius:14px;
                padding:14px 16px; margin:12px 0 20px;'>
        <div style='font-size:10px; color:#30363d; text-transform:uppercase;
                    letter-spacing:1.5px; margin-bottom:6px;'>SESIÓN ACTIVA</div>
        <div style='font-size:16px; font-weight:800; color:#e6edf3; letter-spacing:-0.3px;'>
            <i class='fa-solid {icono}' style='margin-right:8px; color:#E63946;'></i>{usuario.upper()}
        </div>
        <div style='margin-top:6px;'>
            <span style='background:#E63946; color:white; font-size:10px; font-weight:800;
                         padding:3px 10px; border-radius:20px; letter-spacing:0.5px;'>
                {rol.upper()}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Contador de pedidos del día (tiempo real)
    n_hoy = contar_pedidos_hoy()
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#0a4f2b,#062f1a);
                border:1px solid #16462c; border-radius:12px;
                padding:12px 14px; margin-bottom:14px;
                display:flex; align-items:center; justify-content:space-between;'>
        <div>
            <div style='font-size:10px; color:#5fb88a; text-transform:uppercase;
                        letter-spacing:1.5px; font-weight:700;'>
                <i class='fa-solid fa-receipt' style='margin-right:6px;'></i>PEDIDOS HOY
            </div>
            <div style='font-size:26px; font-weight:900; color:#e6edf3; margin-top:2px;'>
                {n_hoy}
            </div>
        </div>
        <i class='fa-solid fa-chart-line' style='font-size:22px; color:#1a9e58; opacity:0.6;'></i>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='font-size:10px; color:#30363d; text-transform:uppercase; "
                "letter-spacing:1.5px; margin:0 0 6px 2px;'>NAVEGACIÓN</p>",
                unsafe_allow_html=True)

    modo = "Venta"
    opciones_piero    = ["Nueva Venta", "Cierre de Caja", "Dashboard", "Admin Productos", "Admin Clientes", "Gestionar Ventas"]
    opciones_cajero   = ["Nueva Venta", "Cierre de Caja", "Gestionar Ventas"]

    if usuario == "piero":
        modo = st.radio("nav", opciones_piero,  label_visibility="hidden")
    elif usuario == "giusseppe":
        modo = st.radio("nav", opciones_cajero, label_visibility="hidden")

    st.markdown("<br>", unsafe_allow_html=True)

    # Hora
    st.markdown(f"""
    <div style='background:#080b10; border:1px solid #1c2128; border-radius:12px;
                padding:12px 14px; margin-bottom:14px; text-align:center;'>
        <div style='font-size:10px; color:#30363d; text-transform:uppercase;
                    letter-spacing:1.5px;'><i class='fa-regular fa-clock' style='margin-right:5px;'></i>HORA</div>
        <div style='font-size:26px; font-weight:900; color:#e6edf3;
                    letter-spacing:2px; margin:2px 0;'>
            {datetime.now().strftime("%H:%M")}
        </div>
        <div style='font-size:11px; color:#484f58; font-weight:500;'>
            {datetime.now().strftime("%d / %m / %Y")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Modo Tablet
    if 'tablet_mode' not in st.session_state:
        st.session_state.tablet_mode = False
    st.session_state.tablet_mode = st.toggle(
        "📱  Modo Tablet (mesero)", value=st.session_state.tablet_mode
    )

    if st.button("🚪  Cerrar Sesión", use_container_width=True):
        logout()

if st.session_state.get('tablet_mode'):
    st.markdown("""
    <style>
    .main div.stButton > button {
        min-height: 110px !important; font-size: 16px !important; font-weight: 800 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 15px !important; padding: 16px 22px !important;
    }
    .stTabs [data-baseweb="tab"] p { font-size: 15px !important; }
    .stCheckbox label p, .stRadio label p { font-size: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def banner_categoria(nombre):
    c1, c2, icon = CAT_META.get(nombre, ('#555','#333','fa-box'))
    label = nombre.replace('_', ' ')
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,{c1},{c2});
                border-radius:14px; padding:14px 20px; margin-bottom:16px;
                display:flex; align-items:center; gap:16px;
                box-shadow:0 6px 20px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
                position:relative; overflow:hidden;'>
        <i class='fa-solid {icon}' style='position:absolute; right:6px; top:8px; font-size:64px;
                    opacity:0.15; transform:rotate(-15deg);'></i>
        <i class='fa-solid {icon}' style='font-size:30px; line-height:1; color:white;
                     filter:drop-shadow(0 3px 6px rgba(0,0,0,0.5));'></i>
        <div>
            <div style='font-size:18px; font-weight:900; color:white;
                        letter-spacing:1px; text-transform:uppercase;'>{label}</div>
            <div style='font-size:11px; color:rgba(255,255,255,0.55);
                        font-weight:600; letter-spacing:0.5px; margin-top:2px;'>
                Selecciona el producto
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def seleccionar_cremas(key_suffix):
    st.markdown("<p style='font-size:11px; font-weight:700; color:#484f58; "
                "text-transform:uppercase; letter-spacing:1.2px; margin:8px 0 4px;'>"
                "🧂  Elige cremas</p>", unsafe_allow_html=True)
    with st.container(border=True):
        sel = []
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.checkbox("Mayonesa", key=f"may_{key_suffix}"): sel.append("Mayonesa")
            if st.checkbox("Ketchup",  key=f"ket_{key_suffix}"): sel.append("Ketchup")
            if st.checkbox("Ají",      key=f"aji_{key_suffix}"): sel.append("Ají")
        with c2:
            if st.checkbox("Tártara",  key=f"tar_{key_suffix}"): sel.append("Tártara")
            if st.checkbox("Mostaza",  key=f"mos_{key_suffix}"): sel.append("Mostaza")
            if st.checkbox("Golf",     key=f"gol_{key_suffix}"): sel.append("Golf")
        with c3:
            if st.checkbox("Ocopa",    key=f"oco_{key_suffix}"): sel.append("Ocopa")
            if st.checkbox("Aceituna", key=f"ace_{key_suffix}"): sel.append("Aceituna")
            if st.checkbox("Todas",    key=f"tod_{key_suffix}"): sel.append("Todas las cremas")
        return ["Todas las cremas"] if "Todas las cremas" in sel else sel

def botones_simples(categoria, key_prefix):
    banner_categoria(categoria)
    items = df_productos[df_productos['Categoria_Auto'] == categoria]
    if items.empty:
        st.info(f"No hay productos en {categoria}")
        return
    cols = st.columns(3)
    for i, row in items.iterrows():
        with cols[i % 3]:
            if st.button(f"{row['PRODUCTO']}\nS/ {row['PRECIO']:.2f}",
                         key=f"{key_prefix}_{i}", use_container_width=True):
                agregar_item(row['PRODUCTO'], row['PRECIO'])

def seccion_header(titulo, subtitulo, icon=None):
    icon_html = f"<i class='fa-solid {icon}' style='margin-right:10px; color:#E63946;'></i>" if icon else ""
    st.markdown(f"""
    <div style='padding:0 0 16px; border-bottom:1px solid #1c2128; margin-bottom:22px;'>
        <h1 style='font-size:20px; font-weight:900; margin:0; color:#e6edf3;
                   letter-spacing:-0.5px;'>{icon_html}{titulo}</h1>
        <p style='color:#484f58; font-size:13px; margin:4px 0 0;'>{subtitulo}</p>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  VISTA: NUEVA VENTA
# ══════════════════════════════════════════════════════════════
if modo in ("Nueva Venta", "Venta"):
    seccion_header("Nueva Venta", "Registra el pedido del cliente", icon="fa-cash-register")

    col_menu, col_ticket = st.columns([1.7, 1])

    with col_menu:
        t1,t2,t3,t4,t5,t6,t7,t8,t9 = st.tabs([
            "🔥 BROAST","🍔 BURGERS","🌭 SALCHI","🍕 PIZZA",
            "🍽️ CARTA","🧊 GASEOSAS","🍹 REFRESCOS","☕ CAFÉ","⭐ EXTRAS"
        ])

        # BROASTERS
        with t1:
            banner_categoria('BROASTERS')
            c1, c2 = st.columns(2)
            with c1: arroz    = st.checkbox("🍚 Con Arroz",    value=True, key="bro_arr")
            with c2: ensalada = st.checkbox("🥗 Con Ensalada", value=True, key="bro_ens")
            cremas = seleccionar_cremas("broaster")
            ac = "Papa"
            if arroz:    ac += ", Arroz"
            if ensalada: ac += ", Ensalada"
            if cremas:   ac += " + (" + ", ".join(cremas) + ")"
            st.divider()
            items = df_productos[df_productos['Categoria_Auto'] == 'BROASTERS']
            cols  = st.columns(2)
            for i, row in items.iterrows():
                with cols[i % 2]:
                    if st.button(f"{row['PRODUCTO']}\nS/ {row['PRECIO']:.2f}",
                                 key=f"b_{i}", use_container_width=True):
                        agregar_item(f"{row['PRODUCTO']} ({ac})", row['PRECIO'])

        # HAMBURGUESAS
        with t2:
            banner_categoria('HAMBURGUESAS')
            st.markdown("<p style='font-size:12px; color:#484f58; margin:-6px 0 8px;'>"
                        "Incluye papas al hilo</p>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: papas    = st.checkbox("🍟 Papas Combinadas", key="ham_pap")
            with c2: ensalada = st.checkbox("🥗 Con Ensalada",     key="ham_ens")
            cremas = seleccionar_cremas("burger")
            ex = (", Papas Combinadas" if papas else "") + (", Ensalada" if ensalada else "")
            cr = (" + (" + ", ".join(cremas) + ")") if cremas else ""
            st.divider()
            items = df_productos[df_productos['Categoria_Auto'] == 'HAMBURGUESAS']
            cols  = st.columns(3)
            for i, row in items.iterrows():
                with cols[i % 3]:
                    if st.button(f"{row['PRODUCTO']}\nS/ {row['PRECIO']:.2f}",
                                 key=f"h_{i}", use_container_width=True):
                        agregar_item(f"{row['PRODUCTO']}{ex}{cr}", row['PRECIO'])

        # SALCHIPAPAS
        with t3:
            banner_categoria('SALCHIPAPAS')
            c1, c2 = st.columns(2)
            with c1: arroz    = st.checkbox("🍚 Con Arroz",    value=True, key="sal_arr")
            with c2: ensalada = st.checkbox("🥗 Con Ensalada", value=True, key="sal_ens")
            cremas = seleccionar_cremas("salchi")
            ac = ""
            if arroz:    ac += ", Arroz"
            if ensalada: ac += ", Ensalada"
            if cremas:   ac += " + (" + ", ".join(cremas) + ")"
            st.divider()
            items = df_productos[df_productos['Categoria_Auto'] == 'SALCHIPAPAS']
            cols  = st.columns(3)
            for i, row in items.iterrows():
                with cols[i % 3]:
                    if st.button(f"{row['PRODUCTO']}\nS/ {row['PRECIO']:.2f}",
                                 key=f"s_{i}", use_container_width=True):
                        agregar_item(row['PRODUCTO'] + (f" ({ac})" if ac else ""), row['PRECIO'])

        with t4: botones_simples('PIZZAS', 'piz')

        # CARTA
        with t5:
            banner_categoria('CARTA')
            c1, c2 = st.columns(2)
            with c1: arroz    = st.checkbox("🍚 Con Arroz",    value=True, key="car_arr")
            with c2: ensalada = st.checkbox("🥗 Con Ensalada", value=True, key="car_ens")
            cremas = seleccionar_cremas("carta")
            ag = []
            if arroz:    ag.append("Arroz")
            if ensalada: ag.append("Ensalada")
            txt = (" con " + ", ".join(ag)) if ag else ""
            if cremas: txt += " + (" + ", ".join(cremas) + ")"
            st.divider()
            items = df_productos[df_productos['Categoria_Auto'] == 'CARTA']
            if items.empty:
                st.info("No hay productos en CARTA")
            else:
                cols = st.columns(3)
                for i, row in items.iterrows():
                    with cols[i % 3]:
                        if st.button(f"{row['PRODUCTO']}\nS/ {row['PRECIO']:.2f}",
                                     key=f"c_{i}", use_container_width=True):
                            agregar_item(f"{row['PRODUCTO']}{txt}", row['PRECIO'])

        with t6: botones_simples('GASEOSAS',   'gas')
        with t7: botones_simples('REFRESCOS',  'ref')
        with t8: botones_simples('INFUSIONES', 'inf')
        with t9: botones_simples('EXTRAS',     'ext')

    # ══ PANEL PEDIDO ══
    with col_ticket:
        with st.container(border=True):
            st.markdown("""
            <div style='display:flex; align-items:center; gap:10px; margin-bottom:16px;'>
                <div style='background:#E63946; border-radius:8px; padding:7px 9px;
                            line-height:1;'><i class='fa-solid fa-receipt' style='color:white; font-size:15px;'></i></div>
                <span style='font-size:17px; font-weight:900; color:#e6edf3;'>
                    Pedido actual
                </span>
            </div>
            """, unsafe_allow_html=True)

            c_busq, c_tipo = st.columns([1.2, 1])
            with c_busq:
                codigo_input = st.text_input("🔍 Buscar cliente", placeholder="Código o celular")
            with c_tipo:
                tipo = st.selectbox("Tipo", ["Mesa", "Llevar", "A pie", "Delivery"])

            nombre_detectado = ""
            direccion_str    = ""
            celular_str      = ""

            if codigo_input:
                _sb = get_supabase()
                _q  = codigo_input.strip()
                _rows = _sb.table("clientes").select("*").or_(
                    f"codigo.ilike.%{_q}%,celular.like.%{_q}%"
                ).limit(5).execute().data
                if _rows:
                    _r = _rows[0]
                    nombre_detectado = _r.get("nombre", "")
                    direccion_str    = _r.get("direccion") or ""
                    celular_str      = _r.get("celular") or ""
                    st.success(f"✅  {nombre_detectado}")
                    if tipo == "Delivery" and direccion_str:
                        st.caption(f"📍  {direccion_str}")

            cliente_final = st.text_input("👤 Nombre del cliente", value=nombre_detectado)
            st.divider()

            if st.session_state.pedido:
                cards_html = "<div style='max-height:230px; overflow-y:auto; margin-bottom:10px;'>"
                for idx, item in enumerate(st.session_state.pedido, 1):
                    nombre = item["Producto"]
                    base, detalle = nombre, ""
                    if "(" in nombre:
                        base, resto = nombre.split("(", 1)
                        base = base.strip()
                        detalle = "(" + resto
                    cards_html += f"""
                    <div style='background:#0d1117; border:1px solid #1c2128; border-left:3px solid #E63946;
                                border-radius:10px; padding:9px 12px; margin-bottom:7px;
                                display:flex; justify-content:space-between; align-items:flex-start; gap:10px;'>
                        <div style='flex:1; min-width:0;'>
                            <div style='font-size:13px; font-weight:800; color:#e6edf3;'>
                                <span style='color:#30363d; font-weight:700; margin-right:5px;'>{idx}.</span>{base}
                            </div>
                            {f"<div style='font-size:11px; color:#8b949e; margin-top:2px; line-height:1.4;'>{detalle}</div>" if detalle else ""}
                        </div>
                        <div style='font-size:13px; font-weight:900; color:#5fb88a; white-space:nowrap;'>
                            S/ {item["Precio"]:.2f}
                        </div>
                    </div>
                    """
                cards_html += "</div>"
                st.html(cards_html)

                if st.button("🗑️  Quitar último ítem"):
                    eliminar_ultimo()

                subtotal    = sum(x["Precio"] for x in st.session_state.pedido)
                costo_envio = 2.0 if tipo == "Delivery" else (1.0 if tipo == "A pie" else 0.0)
                total_final = subtotal + costo_envio

                if costo_envio > 0:
                    st.html(f"""
<div style='background:#080b10; border:1px solid #1c2128;
            border-radius:10px; padding:10px 14px; margin:8px 0;'>
    <div style='display:flex; justify-content:space-between;
                color:#484f58; font-size:13px; margin-bottom:5px;'>
        <span>Subtotal</span><span>S/ {subtotal:.2f}</span>
    </div>
    <div style='display:flex; justify-content:space-between;
                color:#F4A261; font-size:13px; font-weight:700;'>
        <span>🛵  Envío ({tipo})</span>
        <span>+ S/ {costo_envio:.2f}</span>
    </div>
</div>""")

                n_items = len(st.session_state.pedido)
                st.html(f"""
<div style='background:linear-gradient(135deg,#E63946 0%,#a50d1a 100%);
            border-radius:16px; padding:18px 22px; margin:10px 0 10px;
            box-shadow:0 10px 30px rgba(230,57,70,0.5); font-family:Outfit,sans-serif;'>
    <div style='display:flex; justify-content:space-between; align-items:center;'>
        <div>
            <div style='color:rgba(255,255,255,0.6); font-size:10px;
                        font-weight:800; text-transform:uppercase; letter-spacing:2px;'>
                TOTAL A PAGAR
            </div>
            <div style='color:rgba(255,255,255,0.5); font-size:12px; margin-top:3px;'>
                {n_items} producto(s)
            </div>
        </div>
        <div style='color:white; font-size:34px; font-weight:900;
                    letter-spacing:-1px; text-shadow:0 2px 8px rgba(0,0,0,0.3);'>
            S/ {total_final:.2f}
        </div>
    </div>
</div>""")

                pago_mixto = st.toggle("💳  Pago mixto (dos métodos)", value=False, key="toggle_pago_mixto")
                if not pago_mixto:
                    metodo = st.radio("Método de pago", ["Efectivo", "Yape", "Tarjeta"], horizontal=True)
                else:
                    col_ef, col_yp, col_tj = st.columns(3)
                    with col_ef:
                        monto_ef = st.number_input("Efectivo S/", min_value=0.0, step=0.5, value=0.0, key="pago_ef")
                    with col_yp:
                        monto_yp = st.number_input("Yape S/", min_value=0.0, step=0.5, value=0.0, key="pago_yp")
                    with col_tj:
                        monto_tj = st.number_input("Tarjeta S/", min_value=0.0, step=0.5, value=0.0, key="pago_tj")
                    cubierto = monto_ef + monto_yp + monto_tj
                    falta    = total_final - cubierto
                    if abs(falta) < 0.01:
                        st.success(f"Total cubierto S/ {cubierto:.2f} ✓")
                    elif falta > 0:
                        st.warning(f"Faltan S/ {falta:.2f}")
                    else:
                        st.warning(f"Excede S/ {abs(falta):.2f}")
                    partes = []
                    if monto_ef > 0: partes.append(f"Efectivo:{monto_ef:.2f}")
                    if monto_yp > 0: partes.append(f"Yape:{monto_yp:.2f}")
                    if monto_tj > 0: partes.append(f"Tarjeta:{monto_tj:.2f}")
                    metodo = "|".join(partes) if partes else "Efectivo"

                # Ambos usuarios pueden registrar en otra fecha
                fecha_override = None
                if True:
                    cambiar_fecha = st.toggle("📅  Registrar en otra fecha", value=False, key="toggle_fecha")
                    if cambiar_fecha:
                        col_f, col_h = st.columns(2)
                        with col_f:
                            fecha_manual = st.date_input("Fecha", value=datetime.now().date(), key="fecha_manual")
                        with col_h:
                            hora_manual = st.time_input("Hora", value=datetime.now().time(), key="hora_manual", step=60)
                        from datetime import datetime as dt
                        fecha_override = dt.combine(fecha_manual, hora_manual).isoformat()
                        st.caption(f"Se grabará como: {dt.combine(fecha_manual, hora_manual).strftime('%d/%m/%Y %H:%M')}")

                if st.button("✅  CONFIRMAR VENTA", type="primary", use_container_width=True):
                    if not cliente_final:
                        st.error("⚠️  Falta el nombre del cliente")
                    elif pago_mixto and abs((monto_ef + monto_yp + monto_tj) - total_final) > 0.01:
                        st.error("⚠️  El pago mixto no cubre el total exacto")
                    else:
                        with st.spinner("Guardando pedido..."):
                            ok = guardar_venta(
                                usuario       = usuario,
                                cliente       = cliente_final,
                                tipo          = tipo,
                                total         = total_final,
                                direccion     = direccion_str,
                                celular       = celular_str,
                                metodo        = metodo,
                                items         = st.session_state.pedido,
                                fecha_override= fecha_override,
                            )
                            if ok:
                                obtener_datos_ventas.clear()
                                contar_pedidos_hoy.clear()
                                # Ticket de cocina
                                res_print = imprimir_ticket_cocina(
                                    venta_id  = ok,
                                    cliente   = cliente_final,
                                    tipo      = tipo,
                                    items     = st.session_state.pedido,
                                    direccion = direccion_str,
                                    celular   = celular_str,
                                )
                                if res_print is True:
                                    st.toast("🖨️  Ticket enviado a cocina")
                                else:
                                    st.warning(f"🖨️  Ticket no impreso: {res_print}")
                                st.balloons()
                                st.success("Venta registrada correctamente!")
                                st.session_state.pedido = []
                                time.sleep(1)
                                st.rerun()
            else:
                st.html("""
<div style='text-align:center; padding:52px 20px; font-family:Outfit,sans-serif;'>
    <p style='font-size:32px; margin:0 0 12px;'>🛒</p>
    <p style='font-size:14px; font-weight:700; margin:0; color:#21262d;'>Carrito vacío</p>
    <p style='font-size:12px; margin:6px 0 0; color:#161b22;'>Agrega productos desde el menú</p>
</div>""")

# ══════════════════════════════════════════════════════════════
#  VISTA: CIERRE DE CAJA
# ══════════════════════════════════════════════════════════════
elif modo == "Cierre de Caja":
    seccion_header("Cierre de Caja", "Control diario de ventas y movimientos", icon="fa-vault")

    c_btn, c_fec = st.columns([1, 2])
    with c_btn:
        if st.button("🔄  Actualizar", use_container_width=True):
            st.rerun()
    with c_fec:
        fecha_filtro = st.date_input("📅  Día a revisar", datetime.now())

    df_ventas = obtener_datos_ventas()

    if not df_ventas.empty and 'Fecha' in df_ventas.columns:
        fecha_sel = fecha_filtro.strftime("%Y-%m-%d")
        df_ventas['Fecha_Solo'] = df_ventas['Fecha'].astype(str).str.slice(0, 10)
        df_hoy = df_ventas[df_ventas['Fecha_Solo'] == fecha_sel]

        if not df_hoy.empty:
            total_dia  = pd.to_numeric(df_hoy['Total'], errors='coerce').sum()
            col1, col2 = st.columns(2)
            col1.metric(f"Venta Total — {fecha_sel}", f"S/ {total_dia:.2f}")
            col2.metric("Total de Pedidos", len(df_hoy))
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 💳  Desglose por Método de Pago")
            if 'Pago' in df_hoy.columns:
                resumen_pago = {}
                for _, row in df_hoy.iterrows():
                    pago  = str(row['Pago'])
                    total = float(row['Total'])
                    if '|' in pago:
                        for parte in pago.split('|'):
                            m, monto = parte.split(':')
                            resumen_pago[m] = resumen_pago.get(m, 0) + float(monto)
                    else:
                        resumen_pago[pago] = resumen_pago.get(pago, 0) + total
                df_pago = pd.DataFrame(
                    [{"Método": k, "Total": f"S/ {v:.2f}"} for k, v in sorted(resumen_pago.items())]
                )
                st.dataframe(df_pago, hide_index=True, use_container_width=True)
            st.markdown("##### 📋  Todos los Movimientos del Día")
            st.dataframe(df_hoy, hide_index=True, use_container_width=True)
        else:
            st.warning(f"No hay ventas registradas el {fecha_sel}.")
    elif df_ventas.empty:
        st.info("Aún no hay ventas registradas en Supabase. Registra tu primera venta desde 'Nueva Venta'.")
    else:
        st.error("No se pudieron cargar los datos.")

# ══════════════════════════════════════════════════════════════
#  VISTA: DASHBOARD
# ══════════════════════════════════════════════════════════════
elif modo == "Dashboard":
    df_ventas = obtener_datos_ventas()
    dashboard.mostrar_dashboard(df_ventas)

# ══════════════════════════════════════════════════════════════
#  VISTA: ADMIN PRODUCTOS  (solo piero)
# ══════════════════════════════════════════════════════════════
elif modo == "Admin Productos":
    seccion_header("Admin Productos", "Gestiona el catálogo de productos", icon="fa-sliders")
    sb = get_supabase()

    tab_lista, tab_nuevo = st.tabs(["📋  Lista de productos", "➕  Agregar producto"])

    with tab_lista:
        @st.cache_data(ttl=5)
        def _admin_cargar():
            rows = sb.table("productos").select("*").order("categoria").order("codigo").execute().data
            return pd.DataFrame(rows) if rows else pd.DataFrame()

        df_admin = _admin_cargar()

        if df_admin.empty:
            st.info("No hay productos cargados.")
        else:
            cats = ["Todas"] + sorted(df_admin["categoria"].unique().tolist())
            cat_sel = st.selectbox("Filtrar por categoría", cats)
            df_vista = df_admin if cat_sel == "Todas" else df_admin[df_admin["categoria"] == cat_sel]

            for _, row in df_vista.iterrows():
                col_info, col_precio, col_estado, col_del = st.columns([4, 2, 1.5, 1])
                with col_info:
                    st.markdown(f"**{row['nombre']}**  `{row['codigo']}`")
                    st.caption(row["categoria"])
                with col_precio:
                    nuevo_precio = st.number_input(
                        "Precio", value=float(row["precio"]),
                        min_value=0.0, step=0.5, key=f"p_{row['id']}", label_visibility="collapsed"
                    )
                    if nuevo_precio != float(row["precio"]):
                        if st.button("Guardar", key=f"save_{row['id']}"):
                            sb.table("productos").update({"precio": nuevo_precio}).eq("id", row["id"]).execute()
                            st.cache_data.clear()
                            st.rerun()
                with col_estado:
                    activo = st.toggle("Activo", value=bool(row["activo"]), key=f"act_{row['id']}")
                    if activo != bool(row["activo"]):
                        sb.table("productos").update({"activo": activo}).eq("id", row["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{row['id']}", help="Eliminar producto"):
                        sb.table("productos").delete().eq("id", row["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()
                st.divider()

    with tab_nuevo:
        with st.form("form_nuevo_prod", clear_on_submit=True):
            n_codigo   = st.text_input("Código (ej: B09)")
            n_nombre   = st.text_input("Nombre del producto")
            n_precio   = st.number_input("Precio (S/)", min_value=0.0, step=0.5)
            n_categoria = st.selectbox("Categoría", [
                "BROASTERS", "HAMBURGUESAS", "SALCHIPAPAS", "PIZZAS",
                "CARTA", "GASEOSAS", "REFRESCOS", "INFUSIONES", "EXTRAS"
            ])
            submitted = st.form_submit_button("Agregar producto", type="primary", use_container_width=True)
            if submitted:
                if not n_codigo or not n_nombre:
                    st.error("Codigo y nombre son obligatorios.")
                else:
                    try:
                        sb.table("productos").insert({
                            "codigo": n_codigo.upper().strip(),
                            "nombre": n_nombre.strip(),
                            "precio": n_precio,
                            "categoria": n_categoria,
                            "activo": True,
                        }).execute()
                        cargar_datos_supabase.clear()
                        st.cache_data.clear()
                        st.success(f"Producto '{n_nombre}' agregado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════
#  VISTA: ADMIN CLIENTES  (solo piero)
# ══════════════════════════════════════════════════════════════
elif modo == "Admin Clientes":
    seccion_header("Admin Clientes", "Gestiona la base de clientes", icon="fa-users")
    sb = get_supabase()

    tab_lista, tab_nuevo = st.tabs(["📋  Lista de clientes", "➕  Agregar cliente"])

    with tab_lista:
        busqueda = st.text_input("🔍  Buscar por nombre, código o celular", placeholder="Ej: CARMEN o 942...")

        @st.cache_data(ttl=5)
        def _admin_clientes():
            rows = sb.table("clientes").select("*").order("nombre").execute().data
            return pd.DataFrame(rows) if rows else pd.DataFrame()

        df_cli = _admin_clientes()

        if df_cli.empty:
            st.info("No hay clientes cargados.")
        else:
            if busqueda:
                mask = (
                    df_cli["nombre"].str.contains(busqueda, case=False, na=False) |
                    df_cli["codigo"].str.contains(busqueda, case=False, na=False) |
                    df_cli["celular"].fillna("").str.contains(busqueda, na=False)
                )
                df_vista = df_cli[mask]
            else:
                df_vista = df_cli.head(50)
                st.caption(f"Mostrando 50 de {len(df_cli)} clientes. Usa el buscador para filtrar.")

            for _, row in df_vista.iterrows():
                with st.expander(f"{row['nombre']}  ·  {row['codigo']}  ·  {row['celular'] or '—'}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_nombre = st.text_input("Nombre", value=row["nombre"] or "", key=f"cn_{row['id']}")
                        nuevo_cel    = st.text_input("Celular", value=row["celular"] or "", key=f"cc_{row['id']}")
                    with col2:
                        nueva_dir = st.text_input("Dirección", value=row["direccion"] or "", key=f"cd_{row['id']}")
                        nuevo_cod = st.text_input("Código", value=row["codigo"] or "", key=f"cco_{row['id']}")

                    col_save, col_del = st.columns([3, 1])
                    with col_save:
                        if st.button("💾  Guardar cambios", key=f"csave_{row['id']}", use_container_width=True):
                            sb.table("clientes").update({
                                "nombre":    nuevo_nombre.strip(),
                                "celular":   nuevo_cel.strip() or None,
                                "direccion": nueva_dir.strip() or None,
                                "codigo":    nuevo_cod.strip().upper(),
                            }).eq("id", row["id"]).execute()
                            cargar_datos_supabase.clear()
                            st.cache_data.clear()
                            st.success("Cliente actualizado.")
                            st.rerun()
                    with col_del:
                        if st.button("🗑️  Eliminar", key=f"cdel_{row['id']}", use_container_width=True):
                            sb.table("clientes").delete().eq("id", row["id"]).execute()
                            cargar_datos_supabase.clear()
                            st.cache_data.clear()
                            st.rerun()

    with tab_nuevo:
        with st.form("form_nuevo_cli", clear_on_submit=True):
            nc_codigo  = st.text_input("Código (ej: CB1125)")
            nc_nombre  = st.text_input("Nombre completo")
            nc_cel     = st.text_input("Celular (ej: +51 999888777)")
            nc_dir     = st.text_input("Dirección (opcional)")
            submitted  = st.form_submit_button("Agregar cliente", type="primary", use_container_width=True)
            if submitted:
                if not nc_codigo or not nc_nombre:
                    st.error("Código y nombre son obligatorios.")
                else:
                    try:
                        sb.table("clientes").insert({
                            "codigo":    nc_codigo.upper().strip(),
                            "nombre":    nc_nombre.strip(),
                            "celular":   nc_cel.strip() or None,
                            "direccion": nc_dir.strip() or None,
                        }).execute()
                        cargar_datos_supabase.clear()
                        st.cache_data.clear()
                        st.success(f"Cliente '{nc_nombre}' agregado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════
#  VISTA: GESTIONAR VENTAS  (piero: cualquier día / giusseppe: solo hoy)
# ══════════════════════════════════════════════════════════════
elif modo == "Gestionar Ventas":
    seccion_header("Gestionar Ventas", "Anula o edita ventas registradas", icon="fa-pen-to-square")
    sb = get_supabase()

    # Selector de fecha
    if usuario == "piero":
        fecha_sel = st.date_input("📅  Día a gestionar", datetime.now())
    else:
        fecha_sel = datetime.now().date()
        st.markdown(f"**Ventas del día:** {fecha_sel.strftime('%d/%m/%Y')}")

    fecha_str = fecha_sel.strftime("%Y-%m-%d") if hasattr(fecha_sel, 'strftime') else str(fecha_sel)

    @st.cache_data(ttl=5)
    def _ventas_del_dia(fecha):
        rows = (get_supabase().table("ventas")
                .select("*")
                .gte("fecha", fecha + "T00:00:00")
                .lte("fecha", fecha + "T23:59:59")
                .order("fecha", desc=True)
                .execute().data)
        return rows or []

    ventas_dia = _ventas_del_dia(fecha_str)

    if not ventas_dia:
        st.info(f"No hay ventas registradas el {fecha_str}.")
    else:
        total_validas   = sum(v["total"] for v in ventas_dia if not v.get("anulada"))
        total_anuladas  = sum(1 for v in ventas_dia if v.get("anulada"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas del día", len(ventas_dia))
        c2.metric("Total válido", f"S/ {total_validas:.2f}")
        c3.metric("Anuladas", total_anuladas)
        st.divider()

        for v in ventas_dia:
            anulada  = v.get("anulada", False)
            hora     = str(v["fecha"])[11:16]
            color    = "#3d1010" if anulada else "#0d1117"
            etiqueta = "🚫  ANULADA" if anulada else ""

            with st.expander(f"{'🚫  ANULADA  |  ' if anulada else ''}{v['cliente']}  ·  {hora}  ·  S/ {v['total']:.2f}  ·  {v['metodo']}"):
                if anulada:
                    st.warning("Esta venta está anulada y no se incluye en los totales.")
                    if st.button("↩️  Reactivar venta", key=f"reac_{v['id']}"):
                        sb.table("ventas").update({"anulada": False}).eq("id", v["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()
                else:
                    col_info, col_edit = st.columns([1, 1])
                    with col_info:
                        st.markdown(f"**Cliente:** {v['cliente']}")
                        st.markdown(f"**Tipo:** {v['tipo']}  ·  **Pago:** {v['metodo']}")
                        items = (sb.table("venta_items")
                                 .select("producto")
                                 .eq("venta_id", v["id"])
                                 .execute().data)
                        for it in items:
                            nombre_item = it["producto"].split("(")[0].strip()
                            st.markdown(f"- {nombre_item}")

                    with col_edit:
                        nuevo_cliente = st.text_input("Cliente", value=v["cliente"], key=f"vc_{v['id']}")
                        nuevo_metodo  = st.selectbox("Método de pago", ["Efectivo", "Yape", "Tarjeta"],
                                                     index=["Efectivo","Yape","Tarjeta"].index(v["metodo"])
                                                     if v["metodo"] in ["Efectivo","Yape","Tarjeta"] else 0,
                                                     key=f"vm_{v['id']}")
                        nuevo_total   = st.number_input("Total (S/)", value=float(v["total"]),
                                                        min_value=0.0, step=0.5, key=f"vt_{v['id']}")

                    col_save, col_anular = st.columns(2)
                    with col_save:
                        if st.button("💾  Guardar cambios", key=f"vsave_{v['id']}", use_container_width=True):
                            sb.table("ventas").update({
                                "cliente": nuevo_cliente.strip(),
                                "metodo":  nuevo_metodo,
                                "total":   nuevo_total,
                            }).eq("id", v["id"]).execute()
                            obtener_datos_ventas.clear()
                            st.cache_data.clear()
                            st.success("Venta actualizada.")
                            st.rerun()
                    with col_anular:
                        if st.button("🚫  Anular venta", key=f"vanu_{v['id']}", use_container_width=True, type="primary"):
                            sb.table("ventas").update({"anulada": True}).eq("id", v["id"]).execute()
                            obtener_datos_ventas.clear()
                            st.cache_data.clear()
                            st.rerun()
