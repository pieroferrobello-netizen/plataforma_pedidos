import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import date as _date, timedelta as _timedelta
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
    # Extraer fecha y hora directo del string crudo (chars 0-9 = fecha, 11-12 = hora)
    # evita que timezone offsets causen NaT en pd.to_datetime y rompan Hora/Bloque
    _raw                 = df['Fecha'].astype(str)
    df['Fecha_Corta']    = pd.to_datetime(_raw.str.slice(0, 10), errors='coerce').dt.date
    df['Hora']           = pd.to_numeric(_raw.str.slice(11, 13), errors='coerce').fillna(0).astype(int)
    df = df.dropna(subset=['Fecha_Corta'])

    df['_Año']    = df['Fecha_Corta'].apply(lambda d: d.year)
    df['_Mes']    = df['Fecha_Corta'].apply(lambda d: d.month)
    df['_Dia']    = df['Fecha_Corta'].apply(lambda d: d.day)
    # Semana dentro del mes con límite Lun-Dom
    def _sem(d):
        primer = _date(d.year, d.month, 1)
        return (d.day + primer.weekday() - 1) // 7 + 1
    df['_Semana'] = df['Fecha_Corta'].apply(_sem)

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
    MESES_ES = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}

    años_disp = sorted(df['_Año'].dropna().unique().tolist(), reverse=True)
    fa1, fa2, fa3, fa4, fa5, fa6 = st.columns([0.6, 0.9, 0.8, 0.9, 1.1, 1.1])

    with fa1:
        f_año = st.selectbox("📅 Año", [str(a) for a in años_disp], index=0)
    f_año = int(f_año)

    df_año = df[df['_Año'] == f_año]
    meses_disp = sorted(df_año['_Mes'].dropna().unique().tolist())
    mes_opciones = ["Todos"] + [MESES_ES[m] for m in meses_disp]

    with fa2:
        f_mes_str = st.selectbox("Mes", mes_opciones, index=0)

    if f_mes_str == "Todos":
        f_mes_num = None
        df_mes    = df_año
        sem_opciones = ["Todas"]
    else:
        f_mes_num    = next(k for k, v in MESES_ES.items() if v == f_mes_str)
        df_mes       = df_año[df_año['_Mes'] == f_mes_num]
        sems_disp    = sorted(df_mes['_Semana'].dropna().unique().tolist())
        sem_opciones = ["Todas"] + [f"Semana {s}" for s in sems_disp]

    with fa3:
        f_sem_str = st.selectbox("Semana", sem_opciones, index=0)

    with fa4:
        canales   = sorted(df['Canal'].dropna().unique().tolist())
        f_canal   = st.selectbox("Canal", ["Todos"] + canales, index=0)
    with fa5:
        clientes  = sorted(df['Cliente'].dropna().astype(str).unique())
        f_cliente = st.multiselect("Cliente", clientes)
    with fa6:
        items_cl  = extraer_texto_limpio(", ".join(df['Items'].dropna().astype(str)))
        EXCL      = ['ENSALADA', 'ARROZ', 'PAPA', 'YUCA', 'CREMA']
        prods_fil = sorted({p.strip() for p in items_cl.split(',')
                            if p.strip() and not any(e in p.upper() for e in EXCL)})
        f_prod    = st.multiselect("Producto", prods_fil)

    df_f = df[df['_Año'] == f_año].copy()
    if f_mes_num is not None:
        df_f = df_f[df_f['_Mes'] == f_mes_num]
    if f_sem_str != "Todas":
        f_sem_num = int(f_sem_str.split()[1])
        df_f = df_f[df_f['_Semana'] == f_sem_num]
    if f_canal != "Todos":
        df_f = df_f[df_f['Canal'] == f_canal]
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

    # ── TENDENCIA + DÍA DE SEMANA ─────────────────────────────────────────────
    _sec("chart-area", "Tendencia de Ingresos")
    c1, c2 = st.columns([3, 2])

    with c1:
        if f_mes_num is None:
            # Sin filtro de mes → agrupar por mes
            df_f['_MesOrd'] = df_f['Fecha_Corta'].apply(lambda d: d.year * 100 + d.month)
            df_f['_MesStr'] = df_f['Fecha_Corta'].apply(
                lambda d: f"{MESES_ES[d.month][:3]} {d.year}")
            df_tend = (df_f.groupby(['_MesOrd', '_MesStr'])
                       .agg(Total=('Total','sum'), Pedidos=('Total','count'))
                       .reset_index().sort_values('_MesOrd'))
            x_vals   = df_tend['_MesStr'].tolist()
            titulo_c = "Ingresos Mensuales"
            lbl_desg = 'Mes'
        else:
            # Con filtro de mes → agrupar por día
            df_tend = (df_f.groupby('Fecha_Corta')
                       .agg(Total=('Total','sum'), Pedidos=('Total','count'))
                       .reset_index().sort_values('Fecha_Corta'))
            df_tend['Fecha_str'] = df_tend['Fecha_Corta'].apply(lambda d: f"{d.day:02d}/{d.month:02d}")
            x_vals   = df_tend['Fecha_str'].tolist()
            titulo_c = "Ingresos Diarios"
            lbl_desg = 'Fecha'

        fig = go.Figure(go.Bar(
            x=x_vals, y=df_tend['Total'],
            marker_color=_RED,
            text=df_tend['Total'].apply(lambda v: f"S/{v:,.0f}"),
            textposition='outside',
            textfont=dict(color='#8b949e', family='Outfit', size=9),
            hovertemplate='<b>%{x}</b><br>S/ %{y:,.2f}<extra></extra>',
        ))
        fig.update_xaxes(tickangle=-45, type='category')
        fig.update_yaxes(tickprefix="S/ ")
        fig.update_layout(uniformtext_minsize=7, uniformtext_mode='hide')
        st.plotly_chart(_dark(fig, titulo_c), use_container_width=True)


    with c2:
        DIAS_ES    = {0:'Lun',1:'Mar',2:'Mié',3:'Jue',4:'Vie',5:'Sáb',6:'Dom'}
        ORDEN_DIAS = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
        df_f['DiaSemana'] = df_f['Fecha_Corta'].apply(lambda d: DIAS_ES[d.weekday()])
        df_dias = (df_f.groupby('DiaSemana')['Total'].sum().reset_index()
                   .assign(DiaSemana=lambda d: pd.Categorical(d['DiaSemana'], categories=ORDEN_DIAS, ordered=True))
                   .sort_values('DiaSemana'))
        fig = px.bar(df_dias, x='DiaSemana', y='Total', text_auto='.2s',
                     color='Total',
                     color_continuous_scale=[[0,'#0d2137'],[0.5,'#1a5276'],[1,'#58a6ff']])
        fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit', size=10),
                          marker_line_width=0)
        fig.update_coloraxes(showscale=False)
        fig.update_xaxes(title_text="")
        fig.update_yaxes(tickprefix="S/ ", title_text="")
        st.plotly_chart(_dark(fig, "Ingresos por Día de Semana"), use_container_width=True)

    # ── OPERACIONES: BLOQUES · CANAL · PAGOS ──────────────────────────────────
    _sec("sliders", "Operaciones")
    c3, c4, c5 = st.columns(3)

    with c3:
        df_bloq = (df_f[df_f['Bloque'] != 'Otros'].groupby('Bloque').size().reset_index(name='Pedidos')
                   .assign(Bloque=lambda d: pd.Categorical(d['Bloque'], categories=ORDEN_BLOQUES, ordered=True))
                   .sort_values('Bloque'))
        fig = px.bar(df_bloq, x='Pedidos', y='Bloque', orientation='h',
                     text_auto=True,
                     color='Pedidos',
                     color_continuous_scale=[[0,'#0d2137'],[0.5,'#1a5276'],[1,'#58a6ff']])
        fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit', size=11),
                          marker_line_width=0)
        fig.update_coloraxes(showscale=False)
        fig.update_xaxes(title_text="Pedidos")
        fig.update_yaxes(title_text="", autorange='reversed')
        st.plotly_chart(_dark(fig, "Pedidos por Horario"), use_container_width=True)

    with c4:
        df_canal = df_f.groupby('Canal')['Total'].sum().reset_index()
        fig = px.pie(df_canal, values='Total', names='Canal', hole=0.55,
                     color='Canal',
                     color_discrete_map={'Mesa': _RED, 'Call Center': '#58a6ff', 'Otros': '#30363d'})
        fig.update_traces(
            textposition='inside', textinfo='percent+label',
            textfont=dict(color='#ffffff', family='Outfit', size=11),
            marker=dict(line=dict(color=_BG, width=3)),
            hovertemplate='<b>%{label}</b><br>S/ %{value:,.2f}<extra></extra>',
        )
        st.plotly_chart(_dark(fig, "Canal de Venta"), use_container_width=True)

    with c5:
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
                resumen_pago[pago.split(':')[0] if ':' in pago else pago] = \
                    resumen_pago.get(pago.split(':')[0] if ':' in pago else pago, 0) + total

        if resumen_pago:
            df_pago     = pd.DataFrame([{"Método": k, "Total": v} for k, v in resumen_pago.items()])
            total_pago  = df_pago['Total'].sum()
            fig = px.pie(df_pago, values='Total', names='Método', hole=0.55,
                         color='Método',
                         color_discrete_map={'Efectivo':'#3fb950','Yape':'#a371f7','Tarjeta':'#58a6ff'})
            fig.update_traces(
                textposition='inside', textinfo='percent+label',
                textfont=dict(color='#ffffff', family='Outfit', size=11),
                marker=dict(line=dict(color=_BG, width=3)),
                hovertemplate='<b>%{label}</b><br>S/ %{value:,.2f}<extra></extra>',
            )
            fig.update_layout(annotations=[dict(
                text=f"<b>S/{total_pago:,.0f}</b>",
                x=0.5, y=0.5, font_size=13, showarrow=False,
                font=dict(color='#e6edf3', family='Outfit'),
            )])
            st.plotly_chart(_dark(fig, "Método de Pago"), use_container_width=True)

    # ── TOP CLIENTES ───────────────────────────────────────────────────────────
    _sec("users", "Mejores Clientes")
    mask_anon = df_f['Cliente'].str.contains('SALON|CB000|CLIENTE', case=False, na=False)
    df_top = (df_f[~mask_anon].groupby('Cliente')['Total'].sum()
              .reset_index().sort_values('Total', ascending=True).tail(8))
    if not df_top.empty:
        fig = px.bar(df_top, x='Total', y='Cliente', orientation='h',
                     text_auto='.2s',
                     color='Total',
                     color_continuous_scale=[[0,'#3d2800'],[0.5,'#7d5a00'],[1,'#d29922']])
        fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit'),
                          marker_line_width=0,
                          hovertemplate='<b>%{y}</b><br>S/ %{x:,.2f}<extra></extra>')
        fig.update_coloraxes(showscale=False)
        fig.update_xaxes(tickprefix="S/ ", title_text="Total Consumido (S/)")
        fig.update_yaxes(title_text="")
        st.plotly_chart(_dark(fig, "Top 8 Clientes por Monto"), use_container_width=True)

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

        lista_comida = obtener_lista_comida_principal()
        BEBIDAS = ['CHICHA','FANTA','INKA','COCA','AGUA','MARACUYA','CRUSH',
                   'SPRITE','INFUSION','TE ','CAFE','MANZANILLA','GASEOSA','KOLA','CHORIPAN']
        def es_comida(p):
            return (p.upper() in lista_comida) if lista_comida else not any(b in p.upper() for b in BEBIDAS)

        cp, cq = st.columns(2)

        with cp:
            top8 = df_rank.sort_values('_ing', ascending=True).tail(8).copy()
            top8['_lbl'] = top8['_ing'].apply(lambda v: f"S/{v:,.0f}")
            fig  = px.bar(top8, x='_ing', y='Producto', orientation='h',
                          text='_lbl', custom_data=['Cantidad'],
                          color='_ing',
                          color_continuous_scale=[[0,'#0d3320'],[0.5,'#1a6640'],[1,'#39d353']])
            fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit', size=11),
                              marker_line_width=0,
                              hovertemplate='<b>%{y}</b><br>Cantidad: %{customdata[0]}<extra></extra>')
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(tickprefix="S/ ", title_text="Ingreso Estimado (S/)")
            fig.update_yaxes(title_text="")
            st.plotly_chart(_dark(fig, "Top 8 — Mayor Ingreso"), use_container_width=True)

        with cq:
            df_comida = df_rank[df_rank['Producto'].apply(es_comida) & (df_rank['_ing'] > 0)]
            bot8 = df_comida.sort_values('_ing', ascending=False).tail(8).sort_values('_ing').copy()
            bot8['_lbl'] = bot8['_ing'].apply(lambda v: f"S/{v:,.0f}")
            fig  = px.bar(bot8, x='_ing', y='Producto', orientation='h',
                          text='_lbl', custom_data=['Cantidad'],
                          color='_ing',
                          color_continuous_scale=[[0,_RED],[0.5,'#a50d1a'],[1,'#3d0709']])
            fig.update_traces(textfont=dict(color='#e6edf3', family='Outfit', size=11),
                              marker_line_width=0,
                              hovertemplate='<b>%{y}</b><br>Cantidad: %{customdata[0]}<extra></extra>')
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(tickprefix="S/ ", title_text="Ingreso Estimado (S/)")
            fig.update_yaxes(title_text="")
            st.plotly_chart(_dark(fig, "Bottom 8 — Menor Ingreso"), use_container_width=True)

    except Exception as e:
        st.error(f"Error en ranking de productos: {e}")
