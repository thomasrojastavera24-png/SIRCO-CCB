"""
SIRCO v2.0 - Cliente de automatización CCB (versión robusta)
Consulta la plataforma CCB usando Playwright + JavaScript sobre Angular.

Mejoras v2.1:
  - Búsqueda dinámica del componente Angular (no depende del índice [8])
  - Clic en "Búsqueda Avanzada" + espera real antes de interactuar
  - Reintentos automáticos (máx. 3) con mensajes amigables al usuario
  - Separación entre error_usuario y error_tecnico
"""
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

# Playwright es opcional: no disponible en Streamlit Cloud
try:
    from playwright.sync_api import (
        sync_playwright, Page, Browser,
        TimeoutError as PWTimeout,
    )
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False
    Page = None
    Browser = None
    PWTimeout = Exception

from core.config import (
    CCB_URL,
    WAIT_AFTER_SEARCH,
    WAIT_AFTER_TRAMITES,
)

MAX_REINTENTOS   = 3
TIMEOUT_ELEMENTO = 15_000   # ms — espera máx. para un selector


# ─────────────────────────────────────────────
# Estructuras de datos
# ─────────────────────────────────────────────

@dataclass
class Tramite:
    numero: str
    tipo: str
    descripcion: str
    fecha: str


@dataclass
class ResultadoCCB:
    nit: str
    nombre_ccb: str
    tiene_tramites: bool
    tramites: list[Tramite] = field(default_factory=list)
    incidencia: str = ""
    error: str = ""           # Mensaje amigable para mostrar al usuario
    error_tecnico: str = ""   # Detalle técnico (solo para logs y reportes)


# ─────────────────────────────────────────────
# JavaScript — bajo nivel
# ─────────────────────────────────────────────

# Verifica que el campo NIT sea visible en pantalla
JS_FORM_READY = """
() => {
    const el = document.getElementById('txtnumIdentificacion');
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
}
"""

# Escanea __ngContext__ dinámicamente para encontrar el componente Angular
# que tiene form.controls.numIdentificacion y el método consultaAvanzada.
# Devuelve { ok: bool, error: string }
JS_SET_NIT = """
(nit) => {
    const el = document.getElementById('txtnumIdentificacion');
    if (!el) return { ok: false, error: 'Campo #txtnumIdentificacion no encontrado en el DOM' };

    const ctx = el.__ngContext__;
    if (!ctx) return { ok: false, error: 'Angular __ngContext__ no disponible (¿formulario cargado?)' };

    let component = null;
    for (let i = 0; i < ctx.length; i++) {
        try {
            const c = ctx[i];
            if (c && typeof c === 'object'
                && c.form && c.form.controls
                && c.form.controls['numIdentificacion']
                && typeof c.consultaAvanzada === 'function') {
                component = c;
                break;
            }
        } catch (e) { /* ignorar índices no válidos */ }
    }

    if (!component) {
        return {
            ok: false,
            error: 'Componente Angular con form.controls no encontrado. '
                 + 'Longitud de contexto: ' + ctx.length
        };
    }

    try {
        component.form.controls['numIdentificacion'].setValue(nit);
        component.consultaAvanzada();
        return { ok: true, error: '' };
    } catch (e) {
        return { ok: false, error: 'Error al invocar consultaAvanzada: ' + e.message };
    }
}
"""

# Lee razón social del primer resultado de la tabla 0
JS_GET_NOMBRE = """
() => {
    const tables = document.querySelectorAll('table');
    if (!tables || tables.length === 0) return '';
    const rows = tables[0].querySelectorAll('tr');
    if (rows.length < 2) return '';
    const cols = rows[1].querySelectorAll('td');
    return cols.length >= 2 ? cols[1].innerText.trim() : '';
}
"""

# Lee matrícula del primer resultado de la tabla 0
JS_GET_MATRICULA = """
() => {
    const tables = document.querySelectorAll('table');
    if (!tables || tables.length === 0) return '';
    const rows = tables[0].querySelectorAll('tr');
    if (rows.length < 2) return '';
    const cols = rows[1].querySelectorAll('td');
    return cols.length >= 1 ? cols[0].innerText.trim() : '';
}
"""

# Escanea __ngContext__ para encontrar el método consultaTramitesMatricula
# Devuelve { ok: bool, error: string }
JS_VER_TRAMITES = """
(matricula) => {
    const el = document.getElementById('txtnumIdentificacion');
    if (!el) return { ok: false, error: 'Campo NIT no encontrado' };

    const ctx = el.__ngContext__;
    if (!ctx) return { ok: false, error: 'Angular __ngContext__ no disponible' };

    let component = null;
    for (let i = 0; i < ctx.length; i++) {
        try {
            const c = ctx[i];
            if (c && typeof c === 'object'
                && typeof c.consultaTramitesMatricula === 'function') {
                component = c;
                break;
            }
        } catch (e) { /* ignorar */ }
    }

    if (!component) {
        return { ok: false, error: 'Método consultaTramitesMatricula no encontrado en contexto Angular' };
    }

    try {
        component.consultaTramitesMatricula(matricula);
        return { ok: true, error: '' };
    } catch (e) {
        return { ok: false, error: 'Error en consultaTramitesMatricula: ' + e.message };
    }
}
"""

# Lee la tabla de trámites (tabla 1)
JS_LEER_TRAMITES = """
() => {
    const tables = document.querySelectorAll('table');
    if (tables.length < 2) return [];
    const rows = tables[1].querySelectorAll('tr');
    const result = [];
    for (let i = 1; i < rows.length; i++) {
        const cols = rows[i].querySelectorAll('td');
        if (cols.length >= 4) {
            result.push({
                numero:      cols[0].innerText.trim(),
                tipo:        cols[1].innerText.trim(),
                descripcion: cols[2].innerText.trim(),
                fecha:       cols[3].innerText.trim()
            });
        }
    }
    return result;
}
"""


# ─────────────────────────────────────────────
# Cliente principal
# ─────────────────────────────────────────────

class CCBClient:
    """
    Abre un navegador Chromium y consulta la plataforma CCB.

    Uso como context manager:
        with CCBClient() as client:
            resultado = client.consultar_nit("811039217", "2")
    """

    def __init__(self, headless: bool = True):
        # headless=True por defecto — requerido en Streamlit Cloud y entornos sin pantalla
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    def __enter__(self):
        if not PLAYWRIGHT_OK:
            raise RuntimeError(
                "No fue posible ejecutar la consulta real en este entorno. "
                "Use Modo Presentación."
            )
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
        except Exception as exc:
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
            raise RuntimeError(
                "No fue posible ejecutar la consulta real en este entorno. "
                "Use Modo Presentación."
            ) from exc
        self._page = self._browser.new_page()
        self._cargar_pagina()
        return self

    def __exit__(self, *args):
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    # ── Carga y preparación ──────────────────────────────────────────────────

    def _cargar_pagina(self) -> None:
        """Navega a la URL CCB y prepara el formulario avanzado."""
        page = self._page
        page.goto(CCB_URL)
        page.wait_for_load_state("networkidle")
        self._preparar_formulario()

    def _preparar_formulario(self, log: Optional[Callable] = None) -> bool:
        """
        Asegura que el formulario de búsqueda avanzada esté visible y listo.
        1. Si el campo NIT ya es visible → OK directo.
        2. Si no, busca y hace clic en 'Búsqueda Avanzada'.
        3. Reintenta hasta MAX_REINTENTOS veces recargando la página.
        Devuelve True si el formulario quedó listo.
        """
        page = self._page

        def _log(msg):
            if log:
                log(msg)

        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                # ¿Ya está visible el campo NIT?
                try:
                    page.wait_for_selector("#txtnumIdentificacion", timeout=3_000)
                    if page.evaluate(JS_FORM_READY):
                        return True
                except PWTimeout:
                    pass

                # Intentar clic en "Búsqueda Avanzada"
                selectores_avanzada = [
                    "text=Búsqueda Avanzada",
                    "text=Busqueda Avanzada",
                    "a:has-text('Avanzada')",
                    "button:has-text('Avanzada')",
                    "span:has-text('Avanzada')",
                    "li:has-text('Avanzada')",
                ]
                for sel in selectores_avanzada:
                    try:
                        page.wait_for_selector(sel, timeout=4_000)
                        page.click(sel)
                        break
                    except PWTimeout:
                        continue

                # Esperar campo NIT tras el clic
                page.wait_for_selector("#txtnumIdentificacion", timeout=TIMEOUT_ELEMENTO)
                if page.evaluate(JS_FORM_READY):
                    return True

            except Exception:
                pass

            if intento < MAX_REINTENTOS:
                _log(f"  No fue posible acceder al formulario avanzado. Intentando recargar... ({intento}/{MAX_REINTENTOS})")
                try:
                    page.reload()
                    page.wait_for_load_state("networkidle")
                except Exception:
                    pass

        return False

    # ── Consulta individual ──────────────────────────────────────────────────

    def consultar_nit(
        self,
        nit_base: str,
        dv: str,
        nombre_esperado: str = "",
        callback_progreso: Optional[Callable[[str], None]] = None,
    ) -> ResultadoCCB:
        """
        Consulta un NIT en CCB y devuelve un ResultadoCCB con trámites.
        Implementa reintentos automáticos con mensajes amigables.
        """
        page = self._page
        nit_completo = f"{nit_base}-{dv}" if dv else nit_base

        def log(msg):
            if callback_progreso:
                callback_progreso(msg)

        log(f"Consultando NIT {nit_completo}...")

        ultimo_error_tec = ""

        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                resultado = self._intentar_consulta(
                    page, nit_base, dv, nombre_esperado, log
                )
                if resultado is not None:
                    return resultado

                # resultado None → formulario no estaba listo
                if intento < MAX_REINTENTOS:
                    log(f"  La página de la CCB está tardando en cargar. Reintentando consulta... ({intento}/{MAX_REINTENTOS})")
                    self._preparar_formulario(log)

            except Exception as exc:
                ultimo_error_tec = str(exc)
                if intento < MAX_REINTENTOS:
                    log(f"  No fue posible acceder al formulario avanzado. Intentando recargar... ({intento}/{MAX_REINTENTOS})")
                    try:
                        page.reload()
                        page.wait_for_load_state("networkidle")
                        self._preparar_formulario(log)
                    except Exception:
                        pass
                else:
                    log("  Consulta no completada por error técnico de carga en la página de la CCB.")

        return ResultadoCCB(
            nit=nit_completo,
            nombre_ccb="",
            tiene_tramites=False,
            error="Consulta no completada por error técnico de carga en la página de la CCB.",
            error_tecnico=ultimo_error_tec or "MAX_REINTENTOS alcanzado sin éxito.",
        )

    def _intentar_consulta(
        self,
        page: Page,
        nit_base: str,
        dv: str,
        nombre_esperado: str,
        log: Callable,
    ) -> Optional[ResultadoCCB]:
        """
        Ejecuta un intento de consulta.
        Devuelve ResultadoCCB si tuvo éxito (incluyendo "sin resultados").
        Devuelve None si el formulario no estaba listo (señal de reintento).
        Lanza excepción si hay un error técnico grave.
        """
        nit_completo = f"{nit_base}-{dv}" if dv else nit_base

        # 1. Verificar formulario visible
        listo = page.evaluate(JS_FORM_READY)
        if not listo:
            return None  # señal de reintento

        # 2. Ingresar NIT vía Angular
        res_js = page.evaluate(JS_SET_NIT, nit_base)
        if not res_js.get("ok"):
            error_tec = res_js.get("error", "")
            # Si el componente Angular no está listo → reintento
            if any(k in error_tec.lower() for k in ["no encontrado", "no disponible", "contexto"]):
                return None
            # Error real (ej: setValue lanzó excepción)
            return ResultadoCCB(
                nit=nit_completo,
                nombre_ccb="",
                tiene_tramites=False,
                error="No fue posible ingresar el NIT en el formulario de la CCB.",
                error_tecnico=error_tec,
            )

        time.sleep(WAIT_AFTER_SEARCH)

        # 3. Leer nombre y matrícula del primer resultado
        nombre_ccb = page.evaluate(JS_GET_NOMBRE) or ""
        matricula  = page.evaluate(JS_GET_MATRICULA) or ""

        if not matricula:
            log(f"  → Sin resultados para NIT {nit_completo}")
            return ResultadoCCB(
                nit=nit_completo,
                nombre_ccb="",
                tiene_tramites=False,
            )

        # 4. Detectar incidencia de nombre
        incidencia = ""
        if nombre_esperado and nombre_ccb:
            n_ccb = nombre_ccb.upper().replace(".", "").replace(",", "").strip()
            n_esp = nombre_esperado.upper().replace(".", "").replace(",", "").strip()
            if n_ccb not in n_esp and n_esp not in n_ccb:
                incidencia = (
                    f"CCB muestra razón social '{nombre_ccb}' "
                    f"para NIT {nit_completo} (Excel: '{nombre_esperado}')."
                )
                log(f"  ⚠ Incidencia: {incidencia}")

        # 5. Cargar trámites
        log(f"  → Matrícula: {matricula} | CCB: {nombre_ccb}")
        res_tram = page.evaluate(JS_VER_TRAMITES, matricula)
        if not res_tram.get("ok"):
            log(f"  ⚠ Advertencia al cargar trámites: {res_tram.get('error', '')}")

        time.sleep(WAIT_AFTER_TRAMITES)

        # 6. Leer tabla de trámites
        raw_tramites = page.evaluate(JS_LEER_TRAMITES) or []
        tramites = [
            Tramite(
                numero=t["numero"],
                tipo=t["tipo"],
                descripcion=t["descripcion"],
                fecha=t["fecha"],
            )
            for t in raw_tramites
        ]

        tiene_tramites = len(tramites) > 0
        log(f"  → Trámites encontrados: {len(tramites)}")

        return ResultadoCCB(
            nit=nit_completo,
            nombre_ccb=nombre_ccb,
            tiene_tramites=tiene_tramites,
            tramites=tramites,
            incidencia=incidencia,
        )

    # ── Consulta masiva ──────────────────────────────────────────────────────

    def consultar_lote(
        self,
        sociedades: list[dict],
        callback_progreso: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[dict]:
        """
        Consulta una lista de sociedades del Excel.
        Devuelve la misma lista enriquecida con claves:
          resultado_ccb (ResultadoCCB), tramite ("SI"/"NO"), obs (str)
        callback_progreso(actual, total, mensaje)
        """
        total = len(sociedades)
        enriquecidas = []

        for i, soc in enumerate(sociedades, 1):
            if callback_progreso:
                callback_progreso(i, total, f"[{i}/{total}] {soc['nombre']}")

            resultado = self.consultar_nit(
                nit_base=soc["nit_base"],
                dv=soc["dv"],
                nombre_esperado=soc["nombre"],
                callback_progreso=lambda m: (
                    callback_progreso(i, total, m) if callback_progreso else None
                ),
            )

            tramite = "SI" if resultado.tiene_tramites else "NO"
            obs_parts = []
            if resultado.incidencia:
                obs_parts.append(resultado.incidencia)
            for t in resultado.tramites:
                obs_parts.append(
                    f"{t.tipo} Rad.{t.numero} {t.fecha} {t.descripcion}"
                )
            if resultado.error:
                obs_parts.append(resultado.error)

            enriquecidas.append({
                **soc,
                "resultado_ccb": resultado,
                "tramite": tramite,
                "obs": " | ".join(obs_parts),
            })

        return enriquecidas
