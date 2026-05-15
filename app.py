"""
SIRCO v2.0 — Sistema de Revisión Registral CCB
Interfaz Streamlit — compatible con Streamlit Cloud y ejecución local.
"""
import sys
import io
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import PLAYWRIGHT_DISPONIBLE, EXCEL_DEMO_PATH
from core.excel_handler import leer_todas_las_sociedades, guardar_resultados_lote_en_memoria
from core.report_generator import generar_reporte_txt_bytes, generar_reporte_docx_bytes

# ─────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SIRCO v2.0 – Revisión Registral CCB",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-title { font-size:1.8rem; font-weight:700; color:#1a3a5c; }
.sub-title  { font-size:1rem; color:#555; margin-bottom:1.5rem; }
.badge-si   { background:#d4edda; color:#155724; padding:3px 12px; border-radius:12px; font-weight:600; }
.badge-no   { background:#f8d7da; color:#721c24; padding:3px 12px; border-radius:12px; font-weight:600; }
.badge-pend { background:#fff3cd; color:#856404; padding:3px 12px; border-radius:12px; font-weight:600; }
.stat-box   { background:#f0f4f8; border-radius:8px; padding:14px 20px; text-align:center; }
.stat-num   { font-size:2rem; font-weight:700; color:#1a3a5c; }
.stat-lbl   { font-size:0.85rem; color:#666; }
.demo-badge { background:#e8f4f8; border:1px solid #b8d4e0; border-radius:6px;
              padding:6px 14px; color:#1a3a5c; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
st.sidebar.markdown("## ⚖️ SIRCO v2.0")
st.sidebar.markdown("Sistema de Revisión Registral CCB")

if not PLAYWRIGHT_DISPONIBLE:
    st.sidebar.info("🎭 Modo Presentación activo\n\nLas consultas reales a CCB requieren ejecución local con Playwright.")

st.sidebar.divider()

pagina = st.sidebar.radio(
    "Módulo",
    [
        "🏠 Inicio",
        "🎭 Modo Presentación",
        "🔍 Consulta Real CCB",
        "📋 Consulta Masiva",
        "📊 Estado del Excel",
        "📥 Reportes",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("Fuente oficial: CCB en línea")
st.sidebar.caption("https://linea.ccb.org.co/")

# ─────────────────────────────────────────────
# Estado de sesión
# ─────────────────────────────────────────────
if "excel_bytes" not in st.session_state:
    st.session_state.excel_bytes = None
if "sociedades" not in st.session_state:
    st.session_state.sociedades = []
if "resultados_masivos" not in st.session_state:
    st.session_state.resultados_masivos = []


def _cargar_excel_fuente():
    """Devuelve BytesIO del Excel activo (subido o demo)."""
    if st.session_state.excel_bytes:
        return io.BytesIO(st.session_state.excel_bytes)
    if EXCEL_DEMO_PATH.exists():
        return io.BytesIO(EXCEL_DEMO_PATH.read_bytes())
    return None


def _leer_sociedades_activas():
    fuente = _cargar_excel_fuente()
    if fuente is None:
        return []
    try:
        return leer_todas_las_sociedades(fuente)
    except Exception:
        return []


# ══════════════════════════════════════════════
# INICIO
# ══════════════════════════════════════════════
if pagina == "🏠 Inicio":
    st.markdown('<p class="main-title">⚖️ SIRCO v2.0</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Sistema de Revisión Registral — Cámara de Comercio de Bogotá</p>', unsafe_allow_html=True)

    modo_txt = "🎭 Modo Presentación" if not PLAYWRIGHT_DISPONIBLE else "🟢 Consulta real CCB disponible"
    st.markdown(f'<span class="demo-badge">{modo_txt}</span>', unsafe_allow_html=True)
    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ¿Qué hace SIRCO?")
        st.markdown("""
        - **Modo Presentación** — simula consultas y genera informes sin conexión a CCB.
        - **Consulta Individual** — NIT puntual en tiempo real (requiere Playwright local).
        - **Consulta Masiva** — procesa un Excel completo de sociedades.
        - **Reportes** — descarga informe de novedades en `.txt` o `.docx`.
        """)
    with col2:
        st.markdown("### Estado del archivo")
        fuente = _cargar_excel_fuente()
        if fuente:
            socs = _leer_sociedades_activas()
            bogota = [s for s in socs if "bogot" in s["camara"].lower()]
            revisadas = [s for s in bogota if s["tramite"] in ("SI", "NO")]
            con_si = [s for s in bogota if s["tramite"] == "SI"]
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="stat-box"><div class="stat-num">{len(bogota)}</div><div class="stat-lbl">Total Bogotá</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="stat-box"><div class="stat-num">{len(revisadas)}</div><div class="stat-lbl">Revisadas</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="stat-box"><div class="stat-num">{len(con_si)}</div><div class="stat-lbl">Con trámites</div></div>', unsafe_allow_html=True)
            if len(bogota) > len(revisadas):
                st.warning(f"⚠️ {len(bogota) - len(revisadas)} sociedades pendientes de revisión.")
            else:
                st.success("✅ Todas las sociedades Bogotá revisadas.")
        else:
            st.info("Sube un Excel en cualquier módulo o usa los datos de demo.")

    st.divider()
    st.markdown("#### Cargar Excel de seguimiento")
    archivo = st.file_uploader("Sube tu archivo .xlsx", type=["xlsx"], key="upload_inicio")
    if archivo:
        st.session_state.excel_bytes = archivo.read()
        st.session_state.sociedades = []
        st.success(f"✅ Archivo cargado: **{archivo.name}**")


# ══════════════════════════════════════════════
# MODO PRESENTACIÓN
# ══════════════════════════════════════════════
elif pagina == "🎭 Modo Presentación":
    st.markdown("## 🎭 Modo Presentación")
    st.markdown("Simula una consulta CCB y genera informe de novedades. No requiere conexión a internet ni Playwright.")

    st.divider()

    # ── Subsección 1: consulta individual simulada ──
    st.markdown("### 1. Consulta individual simulada")
    with st.form("form_demo"):
        col1, col2 = st.columns([3, 1])
        nit_demo = col1.text_input("NIT (sin dígito de verificación)", placeholder="Ej: 811039217")
        dv_demo  = col2.text_input("DV", placeholder="2", max_chars=1)
        razon    = st.text_input("Razón social", placeholder="Ej: CODESA S.A.")
        tiene_tramite = st.selectbox("Resultado a simular", ["NO — Sin trámites en 2026", "SI — Con trámites en 2026"])
        obs_manual = st.text_area(
            "Observaciones / trámites (opcional)",
            placeholder="Ej: RENOVACION DE MATRICULA Rad.000000261313707 27/03/2026 TRAMITADO",
            height=80,
        )
        simular = st.form_submit_button("🎭 Simular consulta", type="primary")

    if simular and nit_demo:
        es_si = tiene_tramite.startswith("SI")
        st.divider()
        st.markdown(f"**Sociedad consultada:** {razon or '(sin nombre)'}")
        st.markdown(f"**NIT:** {nit_demo}-{dv_demo}")
        if es_si:
            st.markdown('<span class="badge-si">✅ SI — Con trámites en 2026</span>', unsafe_allow_html=True)
            if obs_manual:
                st.info(f"**Trámites registrados:** {obs_manual}")
        else:
            st.markdown('<span class="badge-no">❌ NO — Sin trámites visibles en 2026</span>', unsafe_allow_html=True)

        # Mini informe descargable
        hoy = datetime.today().strftime("%d/%m/%Y")
        fecha_tag = datetime.today().strftime("%d%m%Y")
        soc_demo = [{
            "nombre": razon or f"NIT {nit_demo}",
            "nit_raw": f"{nit_demo}-{dv_demo}",
            "tramite": "SI" if es_si else "NO",
            "obs": obs_manual,
            "resultado_ccb": None,
        }]
        txt_bytes = generar_reporte_txt_bytes(soc_demo, fecha_tag)
        st.download_button(
            "⬇ Descargar informe TXT",
            data=txt_bytes,
            file_name=f"Informe_Demo_{fecha_tag}.txt",
            mime="text/plain",
        )

    st.divider()

    # ── Subsección 2: carga de Excel y procesamiento demo ──
    st.markdown("### 2. Consulta masiva — datos de muestra")

    fuente = _cargar_excel_fuente()
    origen_txt = "archivo de demo incluido" if not st.session_state.excel_bytes else "archivo cargado"

    archivo2 = st.file_uploader("Sube tu propio Excel (opcional)", type=["xlsx"], key="upload_demo")
    if archivo2:
        st.session_state.excel_bytes = archivo2.read()
        st.success(f"✅ Cargado: **{archivo2.name}**")
        fuente = io.BytesIO(st.session_state.excel_bytes)

    if fuente:
        try:
            socs = leer_todas_las_sociedades(fuente)
        except Exception as e:
            st.error(f"Error leyendo el Excel: {e}")
            socs = []

        if socs:
            import pandas as pd
            bogota = [s for s in socs if "bogot" in s["camara"].lower()]
            otras  = [s for s in socs if "bogot" not in s["camara"].lower()]

            st.markdown(f"**Fuente:** {origen_txt} — **{len(socs)} sociedades** encontradas ({len(bogota)} en Bogotá)")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total sociedades", len(socs))
            c2.metric("Bogotá", len(bogota))
            c3.metric("Con trámites (SI)", sum(1 for s in bogota if s["tramite"] == "SI"))
            c4.metric("Sin trámites (NO)", sum(1 for s in bogota if s["tramite"] == "NO"))

            df = pd.DataFrame([{
                "Nombre": s["nombre"],
                "NIT": s["nit_raw"],
                "Cámara": s["camara"],
                "Fecha revisión": s["fecha"],
                "Trámites 2026": s["tramite"] or "Pendiente",
                "Observaciones": s["obs"],
            } for s in socs])

            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("#### Descargar informe de novedades")
            fecha_tag = datetime.today().strftime("%d%m%Y")
            socs_rep = [{**s, "resultado_ccb": None} for s in bogota]

            col_a, col_b = st.columns(2)
            txt_bytes = generar_reporte_txt_bytes(socs_rep, fecha_tag)
            col_a.download_button(
                "⬇ Informe TXT",
                data=txt_bytes,
                file_name=f"Reporte_Trazabilidad_{fecha_tag}.txt",
                mime="text/plain",
                use_container_width=True,
            )
            try:
                docx_bytes = generar_reporte_docx_bytes(socs_rep, fecha_tag)
                col_b.download_button(
                    "⬇ Informe Word",
                    data=docx_bytes,
                    file_name=f"Reporte_Trazabilidad_{fecha_tag}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception:
                col_b.warning("python-docx no disponible.")

            # Excel actualizado descargable
            fuente2 = _cargar_excel_fuente()
            if fuente2 and st.session_state.resultados_masivos:
                excel_out = guardar_resultados_lote_en_memoria(fuente2, st.session_state.resultados_masivos)
                st.download_button(
                    "⬇ Descargar Excel actualizado",
                    data=excel_out,
                    file_name=f"Resultado_CCB_{fecha_tag}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


# ══════════════════════════════════════════════
# CONSULTA REAL CCB
# ══════════════════════════════════════════════
elif pagina == "🔍 Consulta Real CCB":
    st.markdown("## 🔍 Consulta Real CCB")

    if not PLAYWRIGHT_DISPONIBLE:
        st.warning("""
        ⚠️ **Playwright no está disponible en este entorno.**

        Las consultas reales a la CCB requieren ejecución local con el navegador Chromium instalado.

        **Para activar esta función en tu equipo:**
        ```
        pip install playwright
        playwright install chromium
        streamlit run app.py
        ```

        Mientras tanto, usa el módulo **🎭 Modo Presentación** para demostrar la funcionalidad.
        """)
        st.stop()

    # Formulario de consulta real
    with st.form("form_real"):
        col1, col2 = st.columns([3, 1])
        nit_input = col1.text_input("NIT (sin dígito de verificación)", placeholder="Ej: 811039217")
        dv_input  = col2.text_input("DV", placeholder="2", max_chars=1)
        nombre_ref = st.text_input("Razón social (referencia, opcional)")
        buscar = st.form_submit_button("🔍 Consultar en CCB", type="primary")

    if buscar:
        nit_base = nit_input.strip().replace(".", "").replace("-", "").replace(" ", "")
        dv = dv_input.strip()
        if not nit_base:
            st.warning("Por favor ingresa un NIT.")
            st.stop()

        from core.ccb_client import CCBClient
        with st.spinner(f"Consultando NIT {nit_base}-{dv} en CCB..."):
            try:
                with CCBClient(headless=False) as client:
                    resultado = client.consultar_nit(nit_base=nit_base, dv=dv, nombre_esperado=nombre_ref)
            except Exception as e:
                st.error(f"No fue posible conectar con la CCB. Detalle: {e}")
                st.info("Usa el **Modo Presentación** para continuar sin conexión a CCB.")
                st.stop()

        st.divider()
        if resultado.error:
            st.warning(resultado.error)
        else:
            col1, col2 = st.columns([2, 1])
            col1.markdown(f"**Razón social CCB:** {resultado.nombre_ccb or '(no encontrado)'}")
            col1.markdown(f"**NIT consultado:** {resultado.nit}")
            badge = '<span class="badge-si">✅ SI — Con trámites</span>' if resultado.tiene_tramites else '<span class="badge-no">❌ NO — Sin trámites</span>'
            col2.markdown(badge, unsafe_allow_html=True)

            if resultado.incidencia:
                st.warning(f"⚠️ {resultado.incidencia}")

            if resultado.tramites:
                import pandas as pd
                df = pd.DataFrame([{
                    "Número radicado": t.numero,
                    "Tipo": t.tipo,
                    "Descripción": t.descripcion,
                    "Fecha": t.fecha,
                } for t in resultado.tramites])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Sin trámites visibles en el período consultado.")


# ══════════════════════════════════════════════
# CONSULTA MASIVA
# ══════════════════════════════════════════════
elif pagina == "📋 Consulta Masiva":
    st.markdown("## 📋 Consulta Masiva")

    archivo = st.file_uploader("Sube el Excel de seguimiento", type=["xlsx"], key="upload_masiva")
    if archivo:
        st.session_state.excel_bytes = archivo.read()
        st.success(f"✅ Cargado: **{archivo.name}**")

    fuente = _cargar_excel_fuente()
    if not fuente:
        st.info("Sube un Excel para comenzar, o usa **🎭 Modo Presentación** con datos de demo.")
        st.stop()

    try:
        socs = leer_todas_las_sociedades(fuente)
        bogota = [s for s in socs if "bogot" in s["camara"].lower()]
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        st.stop()

    pendientes = [s for s in bogota if s["tramite"] not in ("SI", "NO")]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Bogotá", len(bogota))
    col2.metric("Revisadas", len(bogota) - len(pendientes))
    col3.metric("Pendientes", len(pendientes))

    st.divider()

    if not PLAYWRIGHT_DISPONIBLE:
        st.warning("""
        ⚠️ **Playwright no disponible.** La consulta automática a la CCB no puede ejecutarse aquí.

        Opciones:
        - Usa **🎭 Modo Presentación** para demostrar la funcionalidad.
        - Ejecuta la app localmente con Playwright instalado.
        """)
        st.stop()

    if not pendientes:
        st.success("✅ Todas las sociedades ya fueron revisadas.")
    else:
        st.info(f"Se consultarán **{len(pendientes)}** sociedades pendientes en la CCB.")
        iniciar = st.button("▶ Iniciar consulta CCB", type="primary")

        if iniciar:
            from core.ccb_client import CCBClient
            log_area  = st.empty()
            prog_bar  = st.progress(0)
            prog_text = st.empty()
            log_lines = []
            total = len(pendientes)
            resultados = []

            def agregar_log(msg):
                log_lines.append(msg)
                log_area.text_area("Registro", value="\n".join(log_lines[-25:]), height=180,
                                   key=f"log_{len(log_lines)}")

            try:
                with CCBClient(headless=False) as client:
                    for idx, soc in enumerate(pendientes, 1):
                        prog_bar.progress(idx / total)
                        prog_text.text(f"Consultando {idx}/{total}: {soc['nombre']}")
                        resultado = client.consultar_nit(
                            nit_base=soc["nit_base"], dv=soc["dv"],
                            nombre_esperado=soc["nombre"],
                            callback_progreso=lambda m: agregar_log(f"  {m}"),
                        )
                        tramite = "SI" if resultado.tiene_tramites else "NO"
                        obs_parts = []
                        if resultado.incidencia:
                            obs_parts.append(resultado.incidencia)
                        for t in resultado.tramites:
                            obs_parts.append(f"{t.tipo} Rad.{t.numero} {t.fecha}")
                        if resultado.error:
                            obs_parts.append(resultado.error)
                        resultados.append({**soc, "tramite": tramite, "obs": " | ".join(obs_parts)})

                st.session_state.resultados_masivos = resultados
                fuente2 = _cargar_excel_fuente()
                excel_out = guardar_resultados_lote_en_memoria(fuente2, resultados)
                fecha_tag = datetime.today().strftime("%d%m%Y")
                st.success("✅ Consulta completada.")
                st.download_button("⬇ Descargar Excel actualizado", data=excel_out,
                                   file_name=f"Resultado_CCB_{fecha_tag}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"Error durante la consulta: {e}")


# ══════════════════════════════════════════════
# ESTADO DEL EXCEL
# ══════════════════════════════════════════════
elif pagina == "📊 Estado del Excel":
    st.markdown("## 📊 Estado actual del Excel")

    archivo = st.file_uploader("Sube un Excel (opcional — si no, se usa el demo)", type=["xlsx"], key="upload_estado")
    if archivo:
        st.session_state.excel_bytes = archivo.read()

    socs = _leer_sociedades_activas()
    if not socs:
        st.info("Sube un Excel o ve a **🏠 Inicio** para cargar uno.")
        st.stop()

    import pandas as pd

    df = pd.DataFrame([{
        "#": i,
        "Nombre": s["nombre"],
        "NIT": s["nit_raw"],
        "Cámara": s["camara"],
        "Fecha revisión": s["fecha"],
        "Trámites": s["tramite"] or "Pendiente",
        "Observaciones": s["obs"],
    } for i, s in enumerate(socs, 1)])

    col1, col2 = st.columns(2)
    filtro = col1.selectbox("Filtrar", ["Todos", "SI", "NO", "Pendientes"])
    busq   = col2.text_input("Buscar", placeholder="Nombre o NIT...")

    if filtro == "SI":
        df = df[df["Trámites"] == "SI"]
    elif filtro == "NO":
        df = df[df["Trámites"] == "NO"]
    elif filtro == "Pendientes":
        df = df[~df["Trámites"].isin(["SI", "NO"])]
    if busq:
        mask = df["Nombre"].str.contains(busq, case=False, na=False) | df["NIT"].str.contains(busq, case=False, na=False)
        df = df[mask]

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {len(df)} de {len(socs)} filas.")


# ══════════════════════════════════════════════
# REPORTES
# ══════════════════════════════════════════════
elif pagina == "📥 Reportes":
    st.markdown("## 📥 Generación de Reportes")

    archivo = st.file_uploader("Sube el Excel de seguimiento (opcional)", type=["xlsx"], key="upload_rep")
    if archivo:
        st.session_state.excel_bytes = archivo.read()

    socs = _leer_sociedades_activas()
    if not socs:
        st.info("Sube un Excel o ve a **🏠 Inicio** para cargar uno.")
        st.stop()

    bogota = [s for s in socs if "bogot" in s["camara"].lower()]
    pendientes = [s for s in bogota if s["tramite"] not in ("SI", "NO")]
    if pendientes:
        st.warning(f"⚠️ {len(pendientes)} sociedades sin revisar. El reporte estará incompleto.")

    fecha_tag = st.text_input("Etiqueta de fecha", value=datetime.today().strftime("%d%m%Y"))
    socs_rep = [{**s, "resultado_ccb": None} for s in bogota]

    col1, col2 = st.columns(2)

    if col1.button("📄 Generar TXT", use_container_width=True, type="primary"):
        txt = generar_reporte_txt_bytes(socs_rep, fecha_tag)
        st.download_button("⬇ Descargar TXT", data=txt,
                           file_name=f"Reporte_Trazabilidad_CCB_{fecha_tag}.txt",
                           mime="text/plain")
        with st.expander("Vista previa"):
            st.code(txt.decode("utf-8")[:3000], language="text")

    if col2.button("📝 Generar Word", use_container_width=True):
        try:
            docx = generar_reporte_docx_bytes(socs_rep, fecha_tag)
            st.download_button("⬇ Descargar Word", data=docx,
                               file_name=f"Reporte_Trazabilidad_CCB_{fecha_tag}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"Error generando Word: {e}")
