import streamlit as st
from supabase import create_client, Client
import random

# ============================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ============================================
st.set_page_config(page_title="Tiroteo de Alemán", page_icon="🔫", layout="centered")

# Estilos CSS limpios y adaptados al modo oscuro/claro
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div.block-container {padding-top: 2rem; max-width: 700px;}
    p {margin-bottom: 0.5rem !important;}
    
    /* Contenedores de diseño para las etiquetas */
    .badge-container {
        display: flex;
        gap: 8px;
        margin-bottom: 15px;
    }
    .badge {
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 2. CONEXIÓN A SUPABASE
# ============================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"][cite: 3]
    key = st.secrets["supabase"]["key"][cite: 3]
    return create_client(url, key)[cite: 3]

supabase = init_supabase()[cite: 3]

# DICCIONARIO DE COLORES SEGÚN GÉNERO
GENERO_COLORES = {
    "Masculino": "#3b82f6",  # Azul
    "Femenino": "#ec4899",   # Rosa
    "Neutro": "#10b981",     # Verde
    "Plural": "#8b5cf6"      # Morado
}

# ============================================
# 3. INTERFAZ EN LA BARRA LATERAL (FILTROS)
# ============================================
st.sidebar.title("🎯 Configurar Tiroteo")

filtro_dificultad = st.sidebar.selectbox(
    "Nivel de Dificultad:",
    ["Todos", "Básico", "Intermedio", "Avanzado"]
)

filtro_caso = st.sidebar.selectbox(
    "Caso Gramatical:",
    ["Todos", "Nominativo", "Acusativo", "Dativo", "Genitivo"]
)

# Reiniciar la ronda si se cambian los filtros
if "prev_diff" not in st.session_state or "prev_case" not in st.session_state:
    st.session_state.prev_diff = filtro_dificultad
    st.session_state.prev_case = filtro_caso

if st.session_state.prev_diff != filtro_dificultad or st.session_state.prev_case != filtro_caso:
    st.session_state.prev_diff = filtro_dificultad
    st.session_state.prev_case = filtro_caso
    st.session_state.ronda_num = 1
    st.session_state.current_card = None

# ============================================
# 4. LÓGICA DE FILTRADO Y CARGA ALEATORIA
# ============================================
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False
if "ronda_num" not in st.session_state:
    st.session_state.ronda_num = 1

def fetch_next_card():
    # Construimos la query base hacia la tabla
    query = supabase.table("german_flashcards").select("*")
    
    # Aplicamos los filtros seleccionados directamente en la base de datos
    if filtro_dificultad != "Todos":
        query = query.eq("difficulty", filtro_dificultad)
    if filtro_caso != "Todos":
        query = query.eq("case", filtro_caso)
        
    response = query.execute()
    
    if response.data and len(response.data) > 0:
        st.session_state.current_card = random.choice(response.data)[cite: 3]
        st.session_state.show_solution = False[cite: 3]
    else:
        st.session_state.current_card = None[cite: 3]

if st.session_state.current_card is None:[cite: 3]
    fetch_next_card()[cite: 3]

# ============================================
# 5. INTERFAZ VISUAL PRINCIPAL
# ============================================
if st.session_state.current_card:[cite: 3]
    card = st.session_state.current_card[cite: 3]
    color_genero = GENERO_COLORES.get(card['gender'], '#6b7280')
    
    # Línea 1: Título de ronda limpio[cite: 3]
    st.markdown(f"### 🔫 RONDA {st.session_state.ronda_num} — Palabra: **{card['word']}**")[cite: 3]
    
    # Etiquetas visuales dinámicas (Género, Caso, Dificultad)
    st.markdown(f"""
        <div class="badge-container">
            <span class="badge" style="background-color: {color_genero};">{card['gender'].upper()}</span>
            <span class="badge" style="background-color: #4b5563;">{card['case'].upper()}</span>
            <span class="badge" style="background-color: #1f2937;">{card['difficulty'].upper()}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Línea 2: Contexto o Subcategoría si existe
    if card.get('subcategory'):
        st.markdown(f"**Categoría:** *{card['subcategory']}*")
    st.markdown(f"◦ &nbsp;&nbsp; *Situación:* {card['situation']}")[cite: 3]
    
    # Línea 3: Frase en castellano (Formato gigante limpio)[cite: 3]
    st.markdown(f'<div style="font-size: 24px; font-weight: bold; margin-left: 10px; margin-top: 10px; margin-bottom: 20px; border-left: 4px solid {color_genero}; padding-left: 15px;">"{card["spanish_phrase"]}"</div>', unsafe_allow_html=True)[cite: 3]
    
    # Botonera[cite: 3]
    col1, col2 = st.columns(2)[cite: 3]
    with col1:
        if st.button("👁️ Revelar", use_container_width=True):[cite: 3]
            st.session_state.show_solution = True[cite: 3]
            st.rerun()[cite: 3]
    with col2:
        if st.button("🚀 Siguiente", type="primary", use_container_width=True):[cite: 3]
            st.session_state.ronda_num += 1[cite: 3]
            fetch_next_card()[cite: 3]
            st.rerun()[cite: 3]

    # BLOQUE DE REVELACIÓN (Solo si se ha pulsado Revelar)[cite: 3]
    if st.session_state.show_solution:[cite: 3]
        st.markdown("---") 
        
        # Solución alemana en grande e impactante[cite: 3]
        st.markdown(f"## 🔊 DE: `{card['german_solution']}`")[cite: 3]
        
        # Explicación del caso[cite: 3]
        st.info(f"💡 Explicación:")
        
        # Truco Gramatical adicional si está disponible
        if card.get('grammar_tip'):
            st.warning(f"🔑 Grammar Tip:")

else:
    st.error("No hay tarjetas que coincidan con los filtros seleccionados en la barra lateral.")[cite: 3]
    if st.button("🔄 Recargar / Resetear Filtros"):[cite: 3]
        fetch_next_card()[cite: 3]
        st.rerun()[cite: 3]
