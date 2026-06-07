import streamlit as st
import random
from supabase import create_client, Client

# ============================================
# 1. CONFIGURACIÓN Y ESTILOS DE LA PÁGINA
# ============================================
st.set_page_config(page_title="Declinaciones", page_icon="🔫", layout="centered")

st.html("""
    <style>
    .tabla-container {
        font-family: monospace;
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .tabla-header {
        background-color: #1f2937;
        color: white;
        font-weight: bold;
        text-align: center;
        padding: 8px;
        border: 1px solid #374151;
    }
    .celda-comun {
        padding: 10px;
        text-align: center;
        border: 1px solid #d1d5db;
        background-color: #f9fafb;
        color: #374151;
    }
    .celda-activa {
        padding: 10px;
        text-align: center;
        border: 2px solid #ef4444;
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: bold;
        box-shadow: inset 0 0 8px rgba(239, 68, 68, 0.2);
    }
    .pista-box {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-size: 18px;
    }
    /* El contenedor unificado exacto del script viejo */
    .phrase-box {
        font-size: 24px; 
        font-weight: bold; 
        margin-top: 15px; 
        margin-bottom: 25px; 
        padding-left: 15px;
    }
    </style>
""")

# ============================================
# 2. CONEXIÓN A SUPABASE
# ============================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ============================================
# 3. CARGA DE DATOS DESDE SUPABASE
# ============================================
@st.cache_data(ttl=60)
def get_cards_from_db():
    try:
        response = supabase.table("tarjetas_declinaciones").select(
            "id, caso, genero, pista, spanish_phrase, german_solution"
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        return []

# ============================================
# 4. LAS 3 TABLAS RESUMEN DE APOYO VISUAL
# ============================================
TABLA_ARTICULOS = {
    "Nominativo": {"MASCULINO": "der", "NEUTRO": "das", "FEMENINO": "die", "PLURAL": "die"},
    "Acusativo":  {"MASCULINO": "den", "NEUTRO": "das", "FEMENINO": "die", "PLURAL": "die"},
    "Dativo":     {"MASCULINO": "dem", "NEUTRO": "dem", "FEMENINO": "der", "PLURAL": "den (+n)"},
    "Genitivo":   {"MASCULINO": "des (+s)", "NEUTRO": "des (+s)", "FEMENINO": "der", "PLURAL": "der"}
}

TABLA_DEBIL = {
    "Nominativo": {"MASCULINO": "der gut e", "NEUTRO": "das gut e", "FEMENINO": "die gut e", "PLURAL": "die gut en"},
    "Acusativo":  {"MASCULINO": "den gut en", "NEUTRO": "das gut e", "FEMENINO": "die gut e", "PLURAL": "die gut en"},
    "Dativo":     {"MASCULINO": "dem gut en", "NEUTRO": "dem gut en", "FEMENINO": "der gut en", "PLURAL": "den gut en"},
    "Genitivo":   {"MASCULINO": "des gut en", "NEUTRO": "des gut en", "FEMENINO": "der gut en", "PLURAL": "der gut en"}
}

TABLA_FUERTE = {
    "Nominativo": {"MASCULINO": "gut er", "NEUTRO": "gut es", "FEMENINO": "gut e", "PLURAL": "gut e"},
    "Acusativo":  {"MASCULINO": "gut en", "NEUTRO": "gut es", "FEMENINO": "gut e", "PLURAL": "gut e"},
    "Dativo":     {"MASCULINO": "gut em", "NEUTRO": "gut em", "FEMENINO": "gut er", "PLURAL": "gut en"},
    "Genitivo":   {"MASCULINO": "gut en", "NEUTRO": "gut en", "FEMENINO": "gut er", "PLURAL": "gut er"}
}

TABLA_MIXTA = {
    "Nominativo": {"MASCULINO": "ein gut er", "NEUTRO": "ein gut es", "FEMENINO": "eine gut e", "PLURAL": "meine gut en"},
    "Acusativo":  {"MASCULINO": "einen gut en", "NEUTRO": "ein gut es", "FEMENINO": "eine gut e", "PLURAL": "meine gut en"},
    "Dativo":     {"MASCULINO": "einem gut en", "NEUTRO": "einem gut en", "FEMENINO": "einer gut en", "PLURAL": "meinen gut en"},
    "Genitivo":   {"MASCULINO": "eines gut en", "NEUTRO": "eines gut en", "FEMENINO": "einer gut en", "PLURAL": "meiner gut en"}
}

# ============================================
# 5. CONTROL DE ESTADO (SESSION STATE)
# ============================================
all_cards = get_cards_from_db()

if "tarjeta_actual" not in st.session_state:
    st.session_state.tarjeta_actual = random.choice(all_cards) if all_cards else None
if "revelado" not in st.session_state:
    st.session_state.revelado = False

def siguiente_tarjeta():
    if all_cards:
        st.session_state.tarjeta_actual = random.choice(all_cards)
    st.session_state.revelado = False

# ============================================
# 6. INTERFAZ DE USUARIO PRINCIPAL
# ============================================
st.title("🔫 Tiroteo Rápido de Declinaciones")
st.write("Di la solución en voz alta, compárala con el mismo formato e identifícala visualmente.")
st.markdown("---")

if st.session_state.tarjeta_actual:
    item = st.session_state.tarjeta_actual
    genero_formateado = str(item['genero']).upper() 
    caso_formateado = str(item['caso']).capitalize()

    # Arriba: Pista visual
    st.html(f"""
        <div class="pista-box">
            💡 Base a usar: <b>{item.get('pista', f"{caso_formateado} {genero_formateado}")}</b>
        </div>
    """)

    # CENTRO: BLOQUE DINÁMICO UNIFICADO (Castellano y Alemán en el mismo sitio y formato)
    # Cambia dinámicamente el color del borde de azul (#3b82f6) a verde (#10b981) según el estado
    if st.session_state.revelado:
        st.html(f"""
            <div class="phrase-box" style="border-left: 4px solid #10b981;">
                <span style="color: gray; font-size: 14px; font-weight: normal; display: block; margin-bottom: 4px;">Alemán:</span>
                "{item['german_solution']}"
            </div>
        """)
    else:
        st.html(f"""
            <div class="phrase-box" style="border-left: 4px solid #3b82f6;">
                <span style="color: gray; font-size: 14px; font-weight: normal; display: block; margin-bottom: 4px;">Frase a traducir:</span>
                "{item['spanish_phrase']}"
            </div>
        """)

    # Botonera fija de acciones justo debajo
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ Dar a solución", type="primary", use_container_width=True, disabled=st.session_state.revelado):
            st.session_state.revelado = True
            st.rerun()
    with col2:
        if st.button("🚀 Siguiente frase", use_container_width=True):
            siguiente_tarjeta()
            st.rerun()

    st.markdown("---")

    # ============================================
    # 7. MAPA VISUAL INTERACTIVO
    # ============================================
    st.subheader("🗺️ Localizador en Matriz")
    seleccion = st.radio(
        "Cambia de tabla para ver cómo se comportaría un adjetivo en esta misma casilla:",
        ["Artículos Determinados", "Declinación Débil (con Art.)", "Declinación Fuerte (sin Art.)", "Declinación Mixta (con ein/mein)"],
        horizontal=True
    )

    if seleccion == "Artículos Determinados":
        tabla_activa = TABLA_ARTICULOS
    elif seleccion == "Declinación Débil (con Art.)":
        tabla_activa = TABLA_DEBIL
    elif seleccion == "Declinación Fuerte (sin Art.)":
        tabla_activa = TABLA_FUERTE
    else:
        tabla_activa = TABLA_MIXTA

    casos_orden = ["Nominativo", "Acusativo", "Dativo", "Genitivo"]
    generos_orden = ["MASCULINO", "NEUTRO", "FEMENINO", "PLURAL"]

    html_render = """
    <table class="tabla-container">
        <tr>
            <th class="tabla-header">CASO</th>
            <th class="tabla-header">MASCULINO</th>
            <th class="tabla-header">NEUTRO</th>
            <th class="tabla-header">FEMENINO</th>
            <th class="tabla-header">PLURAL</th>
        </tr>
    """

    for caso in casos_orden:
        html_render += f"<tr><td class='tabla-header'>{caso}</td>"
        for gen in generos_orden:
            if caso_formateado == caso and genero_formateado == gen:
                clase = "celda-activa"
            else:
                clase = "celda-comun"
            
            val_celda = tabla_activa[caso][gen]
            html_render += f"<td class='{clase}'>{val_celda}</td>"
        html_render += "</tr>"

    html_render += "</table>"
    st.html(html_render)

else:
    st.warning("⚠️ No se encontraron frases en la tabla `tarjetas_declinaciones` de Supabase.")
