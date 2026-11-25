"""Dashboard de observabilidad del Agente de Cuenta LATAM (EP3).

Lee los logs que genera EP3_Observabilidad_LATAM.ipynb:
  logs/turnos.jsonl   una línea por consulta (métricas del turno)
  logs/eventos.jsonl  una línea por llamada al LLM, herramienta o request HTTP
  logs/agente.log     registro de ejecución en texto

Ejecutar desde la raíz del repositorio:  streamlit run dashboard/app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

DIR_LOGS = Path(__file__).resolve().parent.parent / "logs"

# Paleta: azul = serie principal, naranja = secundaria, aqua = terciaria; estados con icono + texto
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA_2, BORDE = "#1b2430", "#5b6573", "#e3e7ec"

# Estilo común para todos los gráficos
pio.templates["obs"] = go.layout.Template(layout=dict(
    font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=TINTA_2),
    title=dict(font=dict(size=14, color=TINTA), x=0, xanchor="left", y=0.97),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=8, r=8, t=48, b=8), height=330, bargap=0.35, bargroupgap=0.08,
    xaxis=dict(showgrid=False, linecolor=BORDE, ticks="", zeroline=False),
    yaxis=dict(gridcolor="#eef1f4", zeroline=False, linecolor="rgba(0,0,0,0)"),
    legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, title_text=""),
    hoverlabel=dict(bgcolor="white", bordercolor=BORDE, font=dict(color=TINTA)),
    colorway=[AZUL, NARANJA, AQUA],
))

def sin_titulo_leyenda(fig):
    fig.update_layout(legend_title_text="")
    return fig

pio.templates.default = "plotly_white+obs"
CFG = {"displayModeBar": False}

st.set_page_config(page_title="Observabilidad · Agente LATAM", page_icon="📈", layout="wide")
st.markdown(f"""
<style>
  .block-container {{padding-top: 2rem; padding-bottom: 2rem; max-width: 1400px;}}
  .encabezado {{display:flex; justify-content:space-between; align-items:flex-end; gap:1rem;
               border-bottom:1px solid {BORDE}; padding-bottom:1rem; margin-bottom:1.25rem; flex-wrap:wrap;}}
  .encabezado .titulo {{font-size:1.65rem; font-weight:700; color:{TINTA}; line-height:1.2;}}
  .encabezado .sub {{color:{TINTA_2}; font-size:.92rem; margin-top:.25rem;}}
  .chips span {{display:inline-block; background:#fff; border:1px solid {BORDE}; border-radius:999px;
               padding:.2rem .7rem; margin-left:.35rem; font-size:.8rem; color:{TINTA_2};}}
  .kpi {{background:#fff; border:1px solid {BORDE}; border-radius:12px; padding:.9rem 1rem; height:128px; overflow:hidden;}}
  .kpi .lbl {{white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; color:{TINTA_2}; font-weight:600;}}
  .kpi .val {{white-space:nowrap; font-size:1.7rem; font-weight:700; color:{TINTA}; margin:.25rem 0 .2rem; font-variant-numeric:tabular-nums;}}
  .kpi .nota {{font-size:.8rem; color:{TINTA_2};}}
  .estado {{display:inline-block; font-size:.72rem; font-weight:600; border-radius:6px; padding:.08rem .45rem; margin-right:.35rem;}}
  .ok {{background:#e6f4ea; color:#1e6b35;}} .warn {{background:#fff4e0; color:#8a5300;}} .bad {{background:#fde8e8; color:#a12626;}}
  div[data-testid="stTabs"] button p {{font-size:.95rem; font-weight:600;}}
  div[data-testid="stVerticalBlockBorderWrapper"] {{background:#fff; border-radius:12px;}}
  section[data-testid="stSidebar"] {{border-right:1px solid {BORDE};}}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar(directorio: str):
    d = Path(directorio)
    leer = lambda f: pd.read_json(d / f, lines=True) if (d / f).exists() and (d / f).stat().st_size else pd.DataFrame()
    turnos, eventos = leer("turnos.jsonl"), leer("eventos.jsonl")
    log_txt = (d / "agente.log").read_text(encoding="utf-8") if (d / "agente.log").exists() else ""
    return turnos, eventos, log_txt


def kpi(col, etiqueta, valor, nota="", estado=None):
    chip = ""
    if estado:
        clase, texto = estado
        icono = {"ok": "✓", "warn": "!", "bad": "✕"}[clase]
        chip = f'<span class="estado {clase}">{icono} {texto}</span>'
    col.markdown(f'<div class="kpi"><div class="lbl">{etiqueta}</div><div class="val">{valor}</div>'
                 f'<div class="nota">{chip}{nota}</div></div>', unsafe_allow_html=True)


def semaforo(valor, bueno, aceptable, mayor_es_mejor=True):
    """Umbrales de referencia del equipo para colorear los indicadores."""
    if not mayor_es_mejor:
        valor, bueno, aceptable = -valor, -bueno, -aceptable
    if valor >= bueno:
        return ("ok", "bien")
    return ("warn", "revisar") if valor >= aceptable else ("bad", "crítico")


def encabezado(sub, chips=""):
    st.markdown(f'<div class="encabezado"><div><div class="titulo">Observabilidad · Agente de Cuenta LATAM</div>'
                f'<div class="sub">{sub}</div></div><div class="chips">{chips}</div></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ datos y filtros
with st.sidebar:
    st.markdown("### Filtros")
    directorio = st.text_input("Carpeta de logs", str(DIR_LOGS))
turnos, eventos, log_txt = cargar(directorio)

if turnos.empty:
    encabezado("ISY0101 · Evaluación Parcial 3")
    st.info("No hay logs todavía. Ejecuta `EP3_Observabilidad_LATAM.ipynb` en Colab (módulos 1 a 10), "
            "descarga `logs.zip` y descomprímelo en la carpeta `logs/` del repositorio.")
    st.stop()

turnos = turnos[turnos["previa"] != True].copy()   # la consulta previa del caso de memoria no se evalúa
turnos[["ok_plan", "ok_decision"]] = turnos[["ok_plan", "ok_decision"]].fillna(False).astype(bool)
turnos["herramientas"] = turnos["herramientas"].apply(lambda h: h if isinstance(h, list) else [])

with st.sidebar:
    modelos = sorted(turnos["modelo"].dropna().unique())
    modelo = st.selectbox("Modelo", modelos, index=len(modelos) - 1)
    todos = sorted(turnos["caso"].unique())
    casos_sel = st.multiselect("Casos", todos, default=todos)
turnos = turnos[(turnos["modelo"] == modelo) & turnos["caso"].isin(casos_sel)]
if turnos.empty:
    st.warning("No hay turnos con los filtros elegidos.")
    st.stop()

ev = eventos[eventos["turno_id"].isin(turnos["turno_id"])] if not eventos.empty else pd.DataFrame(columns=["tipo"])
llm, tools, http = (ev[ev["tipo"] == t] for t in ("llm", "herramienta", "http"))
n429 = int((http["estado"] == 429).sum()) if "estado" in http else 0
n_alias = int(tools["alias"].fillna(False).astype(bool).sum()) if "alias" in tools else 0
n_tool_err = int(tools["error"].notna().sum()) if "error" in tools else 0

firma = lambda h: tuple(sorted(set(h)))
cons_caso = turnos.groupby("caso")["herramientas"].apply(lambda s: s.apply(firma).value_counts().iloc[0] / len(s))
fechas = pd.to_datetime(turnos["ts"])

with st.sidebar:
    st.divider()
    st.caption(f"**{len(turnos)}** turnos · **{len(ev)}** eventos  \n"
               f"Ejecución: {fechas.min():%d-%m-%Y %H:%M} → {fechas.max():%H:%M}")

encabezado("Batería de pruebas del agente (ISY0101 · EP3): calidad, latencia, recursos y errores",
           f"<span>Modelo: {modelo}</span><span>{turnos['caso'].nunique()} casos × {turnos['rep'].nunique()} rep.</span>"
           f"<span>{fechas.min():%d-%m-%Y}</span>")

# ------------------------------------------------------------------ KPIs
prec, plan_ok = 100 * turnos["ok_decision"].mean(), 100 * turnos["ok_plan"].mean()
cons, err = 100 * cons_caso.mean(), 100 * turnos["error"].notna().mean()
p50, p95 = turnos["latencia_s"].quantile(.5), turnos["latencia_s"].quantile(.95)
k = st.columns(6, gap="small")
kpi(k[0], "Precisión decisión", f"{prec:.0f}%", f"{turnos['ok_decision'].sum()}/{len(turnos)}", semaforo(prec, 90, 75))
kpi(k[1], "Precisión plan", f"{plan_ok:.0f}%", "temas", semaforo(plan_ok, 90, 75))
kpi(k[2], "Consistencia", f"{cons:.0f}%", "misma ruta", semaforo(cons, 90, 75))
kpi(k[3], "Tasa de error", f"{err:.0f}%", f"{int(turnos['error'].notna().sum())} con excepción", semaforo(err, 0, 10, False))
kpi(k[4], "Latencia p50", f"{p50:.1f} s", f"p95 {p95:.1f} s")
kpi(k[5], "HTTP 429", f"{n429}", "reintentos", semaforo(n429, 0, 10, False))
st.write("")

tab_cal, tab_lat, tab_rec, tab_err = st.tabs(["Calidad", "Latencia", "Recursos", "Errores y logs"])

# ------------------------------------------------------------------ Calidad
with tab_cal:
    por_caso = turnos.groupby("caso").agg(
        variante=("variante", "first"), precision=("ok_decision", "mean"), plan=("ok_plan", "mean"),
        latencia=("latencia_s", "mean"), n=("turno_id", "count"))
    por_caso["consistencia"] = cons_caso
    por_caso[["precision", "plan", "consistencia"]] *= 100
    por_caso["ruta"] = turnos.groupby("caso")["herramientas"].agg(
        lambda s: " → ".join(s.apply(tuple).value_counts().index[0]) or "—")
    with st.container(border=True):
        st.markdown("**Resultado por caso de prueba**")
        st.dataframe(
            por_caso.reset_index()[["caso", "variante", "precision", "consistencia", "plan", "ruta", "latencia", "n"]],
            hide_index=True, use_container_width=True,
            column_config={
                "caso": st.column_config.TextColumn("Caso", width="small"),
                "variante": "Variante",
                "precision": st.column_config.ProgressColumn("Precisión", format="%.0f%%", min_value=0, max_value=100),
                "consistencia": st.column_config.ProgressColumn("Consistencia", format="%.0f%%", min_value=0, max_value=100),
                "plan": st.column_config.ProgressColumn("Plan", format="%.0f%%", min_value=0, max_value=100),
                "ruta": st.column_config.TextColumn("Ruta más frecuente", width="large"),
                "latencia": st.column_config.NumberColumn("Latencia media", format="%.1f s"),
                "n": st.column_config.NumberColumn("Turnos", width="small"),
            })

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1, st.container(border=True):
        st.markdown("**Turnos que no cumplieron lo esperado**")
        fallas = turnos.loc[~turnos["ok_decision"], ["caso", "rep", "motivos", "herramientas", "respuesta"]]
        if fallas.empty:
            st.success("Todos los turnos cumplieron lo esperado.", icon="✅")
        else:
            st.dataframe(fallas, hide_index=True, use_container_width=True, column_config={
                "caso": "Caso", "rep": st.column_config.NumberColumn("Rep.", width="small"),
                "motivos": st.column_config.ListColumn("Motivo", width="large"),
                "herramientas": st.column_config.ListColumn("Herramientas usadas"),
                "respuesta": st.column_config.TextColumn("Respuesta (extracto)")})
    with c2, st.container(border=True):
        uso = turnos.explode("herramientas").dropna(subset=["herramientas"]).reset_index(drop=True)
        conteo = uso["herramientas"].value_counts().sort_values()
        fig = go.Figure(go.Bar(x=conteo.values, y=conteo.index, orientation="h", marker_color=AZUL,
                               marker_cornerradius=4, text=conteo.values, textposition="outside",
                               cliponaxis=False, hovertemplate="%{y}: %{x} usos<extra></extra>"))
        fig.update_layout(title="Uso de herramientas (total)", height=300, xaxis_visible=False,
                          yaxis=dict(gridcolor="rgba(0,0,0,0)"), margin=dict(r=30))
        st.plotly_chart(fig, use_container_width=True, config=CFG)

# ------------------------------------------------------------------ Latencia
with tab_lat:
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        fig = px.strip(turnos, x="caso", y="latencia_s", hover_data=["rep", "variante"],
                       labels={"latencia_s": "segundos", "caso": ""}, title="Latencia por turno (cada punto = 1 turno)")
        fig.update_traces(marker=dict(size=9, color=AZUL, opacity=.8), jitter=.3)
        media = turnos.groupby("caso")["latencia_s"].mean()
        fig.add_scatter(x=media.index, y=media.values, mode="markers", name="media del caso",
                        marker=dict(symbol="line-ew", size=24, line=dict(width=2.5, color=TINTA)))
        fig.add_hline(y=p95, line_dash="dot", line_color=NARANJA, annotation_text=f"p95 {p95:.1f}s",
                      annotation_font_color=TINTA_2)
        st.plotly_chart(fig, use_container_width=True, config=CFG)
    with c2, st.container(border=True):
        if not llm.empty:
            rep = turnos.set_index("turno_id")[["caso", "latencia_s"]].copy()
            rep["LLM"] = llm.groupby("turno_id")["latencia_s"].sum().reindex(rep.index).fillna(0)
            rep["Herramientas"] = tools.groupby("turno_id")["latencia_s"].sum().reindex(rep.index).fillna(0)
            rep["Espera y reintentos"] = (rep["latencia_s"] - rep["LLM"] - rep["Herramientas"]).clip(lower=0)
            rep = rep.groupby("caso")[["LLM", "Herramientas", "Espera y reintentos"]].mean().reset_index()
            fig = px.bar(rep.melt(id_vars="caso", var_name="componente", value_name="s"), x="caso", y="s",
                         color="componente", labels={"s": "segundos (media)", "caso": ""},
                         title="¿Dónde se va el tiempo de cada turno?")
            fig.update_traces(marker_line_color="white", marker_line_width=1.5)
            sin_titulo_leyenda(fig).update_layout(bargap=.3)
            st.plotly_chart(fig, use_container_width=True, config=CFG)
            pct = 100 * llm["latencia_s"].sum() / max(turnos["latencia_s"].sum(), 1e-9)
            st.caption(f"Las llamadas al LLM suman el **{pct:.0f}%** del tiempo total de los turnos.")

    if not tools.empty:
        with st.container(border=True):
            st.markdown("**Latencia por componente**")
            tabla = pd.concat([tools.assign(componente=tools["nombre"]), llm.assign(componente="LLM (cada llamada)")])
            tabla = tabla.groupby("componente")["latencia_s"].agg(
                llamadas="count", media="mean", p50="median", p95=lambda s: s.quantile(.95), max="max")
            st.dataframe(tabla.sort_values("media", ascending=False).reset_index(), hide_index=True,
                         use_container_width=True, column_config={
                             "componente": "Componente", "llamadas": "Llamadas",
                             "media": st.column_config.NumberColumn("Media", format="%.3f s"),
                             "p50": st.column_config.NumberColumn("P50", format="%.3f s"),
                             "p95": st.column_config.NumberColumn("P95", format="%.3f s"),
                             "max": st.column_config.NumberColumn("Máx.", format="%.3f s")})

# ------------------------------------------------------------------ Recursos
with tab_rec:
    r = st.columns(4, gap="small")
    n_llm_turno = llm.groupby("turno_id").size().reindex(turnos["turno_id"]).fillna(0)
    miles = lambda x: f"{x:,.0f}".replace(",", ".")
    kpi(r[0], "Tokens entrada / turno", miles(turnos["tokens_in"].mean()), "prompt + historial + resultados")
    kpi(r[1], "Tokens salida / turno", miles(turnos["tokens_out"].mean()), "razonamiento + respuesta")
    kpi(r[2], "Llamadas al LLM / turno", f"{n_llm_turno.mean():.1f}", f"máximo {int(n_llm_turno.max())}")
    kpi(r[3], "RAM máxima", f"{turnos['rss_mb'].max():.0f} MB", f"base SQLite {turnos['db_kb'].max():.0f} KB")
    st.write("")

    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        tok = turnos.groupby("caso")[["tokens_in", "tokens_out"]].mean().reset_index()
        tok.columns = ["caso", "Entrada", "Salida"]
        fig = px.bar(tok.melt(id_vars="caso", var_name="tipo", value_name="tokens"), x="caso", y="tokens",
                     color="tipo", barmode="group", labels={"caso": ""}, title="Tokens promedio por caso")
        fig.update_traces(marker_cornerradius=4)
        sin_titulo_leyenda(fig).update_layout(bargap=.25, bargroupgap=.05)
        st.plotly_chart(fig, use_container_width=True, config=CFG)
    with c2, st.container(border=True):
        orden = turnos.sort_values("ts").reset_index(drop=True)
        orden["n"] = orden.index + 1
        fig = px.line(orden, x="n", y="rss_mb", markers=True, hover_data=["caso", "rep"],
                      labels={"n": "turno (orden de ejecución)", "rss_mb": "MB"}, title="Memoria RAM del proceso")
        fig.update_traces(line_width=2, marker_size=7, line_color=AZUL)
        st.plotly_chart(fig, use_container_width=True, config=CFG)

# ------------------------------------------------------------------ Errores y logs
with tab_err:
    e = st.columns(4, gap="small")
    n_fallidos = int(turnos["error"].notna().sum())
    kpi(e[0], "Turnos fallidos", n_fallidos, "excepción no controlada", semaforo(n_fallidos, 0, 1, False))
    kpi(e[1], "Reintentos HTTP 429", n429, "límite tokens/min", semaforo(n429, 0, 10, False))
    kpi(e[2], "Herramienta mal escrita", n_alias, "resuelto por el alias", semaforo(n_alias, 0, 3, False))
    kpi(e[3], "Errores en herramientas", n_tool_err, "excepciones en tools", semaforo(n_tool_err, 0, 1, False))
    st.write("")

    c1, c2 = st.columns([2, 3], gap="medium")
    with c1, st.container(border=True):
        if not http.empty:
            h = http.assign(estado=http["estado"].astype(int).astype(str)).groupby(["nombre", "estado"]).size().reset_index(name="n")
            h["servicio"] = h["nombre"].replace({"api.groq.com": "Groq (LLM)",
                                                 "generativelanguage.googleapis.com": "Gemini (embeddings)"})
            fig = px.bar(h, x="n", y="servicio", color="estado", orientation="h", barmode="stack",
                         color_discrete_map={"200": AZUL, "429": NARANJA}, labels={"n": "requests", "servicio": ""},
                         title="Requests HTTP por código de estado")
            sin_titulo_leyenda(fig)
            fig.update_traces(marker_line_color="white", marker_line_width=1.5)
            # Leyenda arriba a la derecha (bajo el título) para que no tape el eje X
            fig.update_layout(height=300, yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                              xaxis=dict(showgrid=True, gridcolor="#eef1f4"),
                              legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
                              margin=dict(t=64))
            st.plotly_chart(fig, use_container_width=True, config=CFG)
        else:
            st.caption("Sin requests HTTP registrados.")
    with c2, st.container(border=True):
        st.markdown("**Registro de ejecución** · `agente.log`")
        nivel = st.segmented_control("Nivel", ["Todos", "WARNING", "ERROR"], default="Todos",
                                     label_visibility="collapsed")
        lineas = [l for l in log_txt.splitlines() if any(t in l for t in turnos["turno_id"])] or log_txt.splitlines()
        if nivel and nivel != "Todos":
            lineas = [l for l in lineas if f" {nivel} " in l]
        st.code("\n".join(lineas[-300:]) or "(sin líneas)", language="log", height=300, wrap_lines=True)
