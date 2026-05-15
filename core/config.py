"""
SIRCO v2.0 - Configuración central
Usa rutas relativas al repositorio — compatible con Streamlit Cloud.
"""
from pathlib import Path

# Raíz del proyecto = carpeta donde vive este repo
BASE_DIR = Path(__file__).resolve().parent.parent

# Carpetas de datos (solo usadas en ejecución local)
DATA_DIR      = BASE_DIR / "data"
REPORTES_DIR  = BASE_DIR / "reportes"

# Excel de demo (incluido en el repo)
EXCEL_DEMO_PATH = DATA_DIR / "sociedades_demo.xlsx"

# Excel de trabajo local (solo disponible en ejecución local)
# En Streamlit Cloud el usuario sube su propio archivo
EXCEL_LOCAL_PATH = BASE_DIR / "data" / "trabajo.xlsx"

# URL CCB
CCB_URL = "https://linea.ccb.org.co/consultaordenes/#/tramites"

# Columnas Excel (índice 0-based en fila de openpyxl)
COL_GRUPO   = 0
COL_NOMBRE  = 1
COL_NIT     = 2
COL_CAMARA  = 3
COL_FECHA   = 4
COL_TRAMITE = 5
COL_OBS     = 6

# Valores
TRAMITE_SI = "SI"
TRAMITE_NO = "NO"

# Tiempos de espera CCB (segundos)
WAIT_AFTER_SEARCH   = 4
WAIT_AFTER_TRAMITES = 4

# Período de revisión (referencia)
PERIODO_DESDE = "01/01/2026"
PERIODO_HASTA = "07/05/2026"

# ¿Playwright disponible? Se detecta al importar.
try:
    import playwright  # noqa: F401
    PLAYWRIGHT_DISPONIBLE = True
except ImportError:
    PLAYWRIGHT_DISPONIBLE = False
