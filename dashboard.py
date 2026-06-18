import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from supabase import create_client

# ── Supabase ─────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_supabase_dash():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

@st.cache_data(ttl=300)
def _cargar_productos_dash():
    try:
        rows = _get_supabase_dash().table("productos").select("codigo,nombre,precio").eq("activo", True).execute().data
        return pd.DataFrame(rows).rename(columns={"codigo": "CODIGO", "nombre": "PRODUCTO", "precio": "PRECIO"})
    except:
        return pd.DataFrame(columns=["CODIGO", "PRODUCTO", "PRECIO"])

@st.cache_data(ttl=300)
def obtener_diccionario_precios():
    try:
        df = _cargar_productos_dash()
        return dict(zip(df['PRODUCTO'].astype(str).str.strip().str.upper(),
                        pd.to_numeric(df['PRECIO'], errors='coerce')))
    except:
        return {}

@st.cache_data(ttl=300)
def obtener_lista_comida_principal():
    try:
        df = _cargar_productos_dash()
        df['CODIGO'] = df['CODIGO'].astype(str).str.upper()
        comidas = df[df['CODIGO'].str.match(r'^[BHSPC]')]
        return comidas['PRODUCTO'].astype(str).str.strip().str.upper().tolist()
    except:
        return []

# ── Helpers de texto ─────────────────────────────────────────────────────────
def extraer_texto_limpio(texto_crudo):
    res, nivel = "", 0
    for char in str(texto_crudo):
        if char in ('(', '['): nivel += 1
        elif char in (')', ']'): nivel = max(0, nivel - 1)
        elif nivel == 0: res += char
    return res.replace('+', ',')

# ── Tema Plotly ───────────────────────────────────────────────────────────────
_BG  = "#0a0d13"
_RED = "#E63946"

_BASE = dict(
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(color="#8b949e", family="Outfit, sans-serif", size=12),
    xaxis=dict(gridcolor="#1c2128", linecolor="#1c2128",
               tickfont=dict(color="#6e7681"), title_font=dict(color="#6e7681")),
    yaxis=dict(gridcolor="#1c2128", linecolor="#1c2128",
               tickfont=dict(color="#6e7681"), title_font=dict(color="#6e7681")),
    margin=dict(l=16, r=16, t=44, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b949e")),
    hoverlabel=dict(bgcolor="#161b22", font_color="#e6edf3", font_family="Outfit"),
)

def _dark(fig, title=""):
    fig.update_layout(
        title=dict(text=title, font=dict(color="#c9d1d9", size=13,
                   family="Outfit", weight=700), x=0, xanchor="left", pad=dict(l=0)),
        **_BASE,
    )
    return fig

def _sec(icon_fa, texto):
    st.html(
        f"<div style='display:flex;align-items:center;gap:10px;margin:28px 0 10px;'>"
        f"<i class='fa-solid fa-{icon_fa}' style='color:#E63946;font-size:11px;'></i>"
        f"<p style='font-size:10px;font-weight:800;color:#484f58;letter-spacing:1.8px;"
        f"text-transform:uppercase;margin:0;font-family:Outfit,sans-serif;'>{texto}</p>"
        f"</div>"
    )

# ── Dashboard principal ───────────────────────────────────────────────────────
def mostrar_dashboard(df_ventas):
    # Header
    st.html("""
<div style='display:flex; align-items:center; gap:14px; margin-bottom:20px;'>
  <div style='background:linear-gradient(135deg,#E63946 0%,#7d0610 100%);
              border-radius:12px; padding:10px 14px; line-height:1; display:flex;align-items:center;justify-content:center;'>
    <i class="fa-solid fa-chart-line" style='color:white;font-size:18px;'></i></div>
  <div>
    <div style='font-size:21px; font-weight:900; color:#e6edf3;
                font-family:Outfit,sans-serif; letter-spacing:-0.3px;'>Dashboard</div>
    <div style='font-size:12px; color:#6e7681; font-family:Outfit,sans-serif;
                margin-top:2px;'>Análisis de operaciones nocturnas · 6 PM – 1 AM</div>
  </div>
</div>
""")

    if df_ventas.empty:
        st.warning("Aún no hay datos registrados.")
        return

    # ── ETL ──────────────────────────────────────────────────────────────────
    df = df_ventas.copy()
    df['Total']          = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
    df['Fecha_Completa'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Fecha_Corta']    = df['Fecha_Completa'].dt.date
    df['Hora']           = df['Fecha_Completa'].dt.hour
    df = df.dropna(subset=['Fecha_Corta'])
    df = df[(df['Hora'] >= 18) | (df['Hora'] < 6)]

    if df.empty:
        st.error("No hay ventas en el horario de atención (18:00 en adelante).")
        return

    def macro(tipo):
        if tipo == 'Mesa': return 'Mesa'
        if tipo in ['Llevar', 'Delivery', 'A pie']: return 'Call Center'
        return 'Otros'
    df['Canal'] = df['Tipo'].apply(macro)

    ORDEN_BLOQUES = ["18:00-19:59", "20:00-21:59", "22:00-23:59",
                     "00:00-01:59", "02:00-03:59", "04:00-05:59"]
    def bloque(hora):
        if 18 <= hora < 20: return "18:00-19:59"
        if 20 <= hora < 22: return "20:00-21:59"
        if 22 <= hora < 24: return "22:00-23:59"
        if  0 <= hora <  2: return "00:00-01:59"
        if  2 <= hora <  4: return "02:00-03:59"
        if  4 <= hora <  6: return "04:00-05:59"
        return "Otros"
    df['Bloque'] = df['Hora'].apply(bloque)

    # ── FILTROS ───────────────────────────────────────────────────────────────
    min_d, max_d = df['Fecha_Corta'].min(), df['Fecha_Corta'].max()
    fc1, fc2, fc3, fc4 = st.columns([1.6, 1, 1, 1])
    with fc1:
        rango = st.date_input("📅  Rango de fechas", [min_d, max_d],
                              min_value=min_d, max_value=max_d)
    with fc2:
        canales   = df['Canal'].unique().tolist()
        f_canal   = st.multiselect("Canal", canales, default=canales)
    with fc3:
        clientes  = sorted(df['Cliente'].dropna().astype(str).unique())
        f_cliente = st.multiselect("Cliente", clientes)
    with fc4:
        items_cl  = extraer_texto_limpio(", ".join(df['Items'].dropna().astype(str)))
        EXCL      = ['ENSALADA', 'ARROZ', 'PAPA', 'YUCA', 'CREMA']
        prods_fil = sorted({p.strip() for p in items_cl.split(',')
                            if p.strip() and not any(e in p.upper() for e in EXCL)})
        f_prod    = st.multiselect("Producto", prods_fil)

    df_f = df.copy()
    if len(rango) == 2:
        df_f = df_f[(df_f['Fecha_Corta'] >= rango[0]) & (df_f['Fecha_Corta'] <= rango[1])]
    if f_canal:
        df_f = df_f[df_f['Canal'].isin(f_canal)]
    if f_cliente:
        df_f = df_f[df_f['Cliente'].isin(f_cliente)]
    if f_prod:
        patron = '|'.join(re.escape(p) for p in f_prod)
        df_f   = df_f[df_f['Items'].str.contains(patron, case=False, na=False)]

    if df_f.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_ing   = df_f['Total'].sum()
    total_ped   = len(df_f)
    ticket_prom = total_ing / total_ped if total_ped > 0 else 0
    hora_punta  = df_f['Bloque'].mode()
    hora_punta  = hora_punta[0] if not hora_punta.empty else "—"
    kpis = [
        ("coins",   "Ingresos Totales", f"S/ {total_ing:,.2f}", "#d29922", "rgba(210,153,34,0.12)"),
        ("receipt", "Pedidos Totales",  f"{total_ped:,}",        "#58a6ff", "rgba(88,166,255,0.12)"),
        ("tag",     "Ticket Promedio",  f"S/ {ticket_prom:.2f}", "#3fb950", "rgba(63,185,80,0.12)"),
        ("fire",    "Horario Punta",    hora_punta,               "#f97316", "rgba(249,115,22,0.12)"),
    ]
    html = "<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:8px 0 4px;'>"
    for fa, label, val, ic, bg in kpis:
        html += f"""
<div style='background:#0d1117;border:1px solid #21262d;border-radius:14px;
            padding:18px 16px;border-top:3px solid #E63946;'>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:12px;'>
    <div style='background:{bg};border-radius:7px;
                width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0;'>
      <i class="fa-solid fa-{fa}" style='color:{ic};font-size:12px;'></i>
    </div>
    <span style='font-size:10px;font-weight:800;color:#484f58;letter-spacing:1.2px;
                 text-transform:uppercase;font-family:Outfit,sans-serif;'>{label}</span>
  </div>
  <div style='font-size:24px;font-weight:900;color:#e6edf3;
              font-family:Outfit,sans-serif;letter-spacing:-0.5px;'>{val}</div>
</div>"""
    html += "</div>"
    st.html(html)

    # ── TENDENCIA + BLOQUES HORARIOS ──────────────────────────────────────────
    _sec("chart-area", "Tendencia e Horarios")
    c1, c2 = st.columns(2)

    with c1:
        df_tend = df_f.groupby('Fecha_Corta')['Total'].sum().reset_index()
        fig = go.Figure(go.Scatter(
            x=df_tend['Fecha_Corta'], y=df_tend['Total'],
            mode='lines+markers',
            line=dict(color=_RED, width=2),
            fill='tozeroy', fillcolor='rgba(230,57,70,0.10)',
            marker=dict(color=_RED, size=5, line=dict(color='#7d0610', width=1)),
            hovertemplate='<b>%{x}</b><br>S/ %{y:,.2f}<extra></extra>',
        ))
        fig.update_xaxes(tickformat="%d %b")
        fig.update_yaxes(tickprefix="S/ ")
        st.plotly_chart(_dark(fig, "Ingresos Diarios"), use_container_width=True)

    with c2:
        df_bloq = (df_f.groupby('Bloque').size().reset_index(name='Pedidos')
                   .assign(Bloque=lambda d: pd.Categorical(d['Bloque'], categories=ORDEN_BLOQUES, ordered=True))
                   .sort_values('Bloque'))
        fig = px.bar(df_bloq, x='Bloque', y='Pedidos', text_auto=True,
                     color='Pedidos',
                     color_continuous_scale=[[0,'#3d0709'],[0.5,'#a50d1a'],[1,_RED]])
        fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit'),
                          marker_line_width=0)
        fig.update_coloraxes(showscale=False)
        fig.update_xaxes(title_text="")
        fig.update_yaxes(title_text="Pedidos")
        st.plotly_chart(_dark(fig, "Pedidos por Bloque Horario"), use_container_width=True)

    # ── CANAL + TOP CLIENTES ──────────────────────────────────────────────────
    _sec("chart-pie", "Canales y Clientes")
    c3, c4 = st.columns(2)

    with c3:
        df_canal = df_f.groupby('Canal')['Total'].sum().reset_index()
        colores  = {'Mesa': _RED, 'Call Center': '#58a6ff', 'Otros': '#30363d'}
        fig = px.pie(df_canal, values='Total', names='Canal', hole=0.55,
                     color='Canal', color_discrete_map=colores)
        fig.update_traces(
            textposition='inside', textinfo='percent+label',
            textfont=dict(color='#ffffff', family='Outfit', size=12),
            marker=dict(line=dict(color=_BG, width=3)),
            hovertemplate='<b>%{label}</b><br>S/ %{value:,.2f}<br>%{percent}<extra></extra>',
        )
        st.plotly_chart(_dark(fig, "Distribución por Canal"), use_container_width=True)

    with c4:
        mask_anon = df_f['Cliente'].str.contains('SALON|CB000|CLIENTE', case=False, na=False)
        df_top = (df_f[~mask_anon].groupby('Cliente')['Total'].sum()
                  .reset_index().sort_values('Total', ascending=True).tail(5))
        if not df_top.empty:
            fig = px.bar(df_top, x='Total', y='Cliente', orientation='h',
                         text_auto='.2s', color_discrete_sequence=[_RED])
            fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit'),
                              marker_line_width=0,
                              hovertemplate='<b>%{y}</b><br>S/ %{x:,.2f}<extra></extra>')
            fig.update_xaxes(tickprefix="S/ ", title_text="Monto Total (S/)")
            fig.update_yaxes(title_text="")
            st.plotly_chart(_dark(fig, "Top 5 Clientes"), use_container_width=True)
        else:
            st.info("No hay datos suficientes de clientes nominados.")

    # ── MÉTODOS DE PAGO ────────────────────────────────────────────────────────
    _sec("credit-card", "Métodos de Pago")
    resumen_pago = {}
    for _, row in df_f.iterrows():
        pago  = str(row.get('Pago', ''))
        total = float(row['Total'])
        if '|' in pago:
            for parte in pago.split('|'):
                try:
                    m, monto = parte.split(':')
                    resumen_pago[m] = resumen_pago.get(m, 0) + float(monto)
                except ValueError:
                    pass
        else:
            metodo = pago.split(':')[0] if ':' in pago else pago
            resumen_pago[metodo] = resumen_pago.get(metodo, 0) + total

    if resumen_pago:
        df_pago = pd.DataFrame([{"Método": k, "Total": v}
                                 for k, v in sorted(resumen_pago.items(),
                                                    key=lambda x: -x[1])])
        total_pago = df_pago['Total'].sum()

        col_m1, col_m2 = st.columns([1, 1.4])
        with col_m1:
            colores_pago = {
                'Efectivo': '#3fb950', 'Yape':    '#a371f7',
                'Tarjeta':  '#58a6ff', 'Mixto':   '#d29922',
            }
            cards = "<div style='display:flex;flex-direction:column;gap:10px;'>"
            for _, r in df_pago.iterrows():
                pct   = r['Total'] / total_pago * 100 if total_pago > 0 else 0
                color = colores_pago.get(r['Método'], '#8b949e')
                cards += f"""
<div style='background:#0d1117;border:1px solid #21262d;border-radius:12px;
            padding:14px 16px;display:flex;justify-content:space-between;align-items:center;'>
  <div style='display:flex;align-items:center;gap:10px;'>
    <div style='width:10px;height:10px;border-radius:50%;background:{color};'></div>
    <div style='font-size:13px;font-weight:700;color:#c9d1d9;font-family:Outfit,sans-serif;'>{r['Método']}</div>
  </div>
  <div style='text-align:right;'>
    <div style='font-size:15px;font-weight:900;color:#e6edf3;font-family:Outfit,sans-serif;'>S/ {r['Total']:,.2f}</div>
    <div style='font-size:10px;color:#6e7681;font-family:Outfit,sans-serif;'>{pct:.1f}%</div>
  </div>
</div>"""
            cards += "</div>"
            st.html(cards)

        with col_m2:
            fig = px.pie(df_pago, values='Total', names='Método', hole=0.6,
                         color='Método',
                         color_discrete_map={
                             'Efectivo': '#3fb950', 'Yape': '#a371f7',
                             'Tarjeta': '#58a6ff',
                         })
            fig.update_traces(
                textposition='inside', textinfo='percent',
                textfont=dict(color='#ffffff', family='Outfit', size=12),
                marker=dict(line=dict(color=_BG, width=3)),
                hovertemplate='<b>%{label}</b><br>S/ %{value:,.2f}<extra></extra>',
            )
            fig.update_layout(
                annotations=[dict(
                    text=f"<b>S/ {total_pago:,.0f}</b>",
                    x=0.5, y=0.5, font_size=15, showarrow=False,
                    font=dict(color='#e6edf3', family='Outfit'),
                )]
            )
            st.plotly_chart(_dark(fig, "Composición de Pagos"), use_container_width=True)

    # ── RANKING DE PRODUCTOS ───────────────────────────────────────────────────
    _sec("trophy", "Ranking de Productos")
    try:
        precios      = obtener_diccionario_precios()
        texto_limpio = extraer_texto_limpio(", ".join(df_f['Items'].astype(str)))
        EXCL         = ['ENSALADA', 'ARROZ', 'PAPA', 'YUCA', 'CREMA']
        lista        = [p.strip() for p in texto_limpio.split(',')
                        if p.strip() and not any(e in p.upper() for e in EXCL)]

        df_rank = pd.Series(lista).value_counts().reset_index()
        df_rank.columns = ['Producto', 'Cantidad']
        df_rank['_ing'] = df_rank.apply(
            lambda r: r['Cantidad'] * precios.get(str(r['Producto']).strip().upper(), 0), axis=1
        )
        df_rank.sort_values('_ing', ascending=False, inplace=True)
        df_rank['Ingreso'] = df_rank['_ing'].apply(lambda x: f"S/ {x:,.2f}")
        cols = ['Producto', 'Cantidad', 'Ingreso']

        top5   = df_rank[cols].head(5)

        lista_comida = obtener_lista_comida_principal()
        BEBIDAS = ['CHICHA','FANTA','INKA','COCA','AGUA','MARACUYA','CRUSH',
                   'SPRITE','INFUSION','TE ','CAFE','MANZANILLA','GASEOSA','KOLA','CHORIPAN']
        def es_comida(p):
            return (p.upper() in lista_comida) if lista_comida else not any(b in p.upper() for b in BEBIDAS)

        bot5 = (df_rank[df_rank['Producto'].apply(es_comida) & (df_rank['_ing'] > 0)]
                [cols].tail(5).iloc[::-1])

        cb, cw = st.columns(2)
        with cb:
            st.html("<p style='font-size:11px;font-weight:800;color:#3fb950;"
                    "letter-spacing:1px;font-family:Outfit,sans-serif;margin:0 0 8px;'>"
                    "▲  TOP 5 — MAYOR INGRESO</p>")
            st.dataframe(top5, hide_index=True, use_container_width=True)
        with cw:
            st.html("<p style='font-size:11px;font-weight:800;color:#E63946;"
                    "letter-spacing:1px;font-family:Outfit,sans-serif;margin:0 0 8px;'>"
                    "▼  BOTTOM 5 — MENOR INGRESO</p>")
            st.dataframe(bot5, hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"Error en ranking de productos: {e}")
