# ⚖️ SIRCO v2.0 — Sistema de Revisión Registral CCB

Herramienta de seguimiento registral corporativo para verificar trámites ante la **Cámara de Comercio de Bogotá (CCB)**.

## Módulos disponibles

| Módulo | Descripción |
|---|---|
| 🎭 **Modo Presentación** | Demo funcional sin conexión a CCB — ideal para presentaciones |
| 🔍 **Consulta Individual** | Ingresa un NIT y consulta en tiempo real (requiere navegador local) |
| 📋 **Consulta Masiva** | Procesa un Excel completo de sociedades |
| 📊 **Estado del Excel** | Visualiza y filtra resultados cargados |
| 📥 **Reportes** | Descarga informe de novedades en TXT o Word |

## Uso en Streamlit Cloud

La app corre en **Modo Presentación** de forma predeterminada.  
Las consultas reales a la CCB requieren ejecución local con Playwright instalado.

## Ejecución local

```bash
pip install -r requirements.txt
pip install playwright
playwright install chromium
streamlit run app.py
```

## Estructura del proyecto

```
SIRCO_APP/
├── app.py                  ← Interfaz principal
├── requirements.txt
├── data/
│   └── sociedades_demo.xlsx  ← Excel de muestra
├── core/
│   ├── config.py
│   ├── ccb_client.py       ← Automatización CCB (requiere Playwright)
│   ├── excel_handler.py
│   └── report_generator.py
└── .streamlit/
    └── config.toml
```

---
*Desarrollado para Contexto Legal S.A. — SIRCO v2.0*
