import streamlit as st
from supabase import create_client, Client
import random

# 1. Configuración de la página (Dejamos los menús por defecto activos)
st.set_page_config(
    page_title="Tiroteo de Alemán", 
    page_icon="🔫", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Conexión a Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# 3. Filtros en la Barra Lateral
st.sidebar.title("🎯 Configurar Tiroteo")

filtro_dificultad = st.sidebar.selectbox(
    "Nivel de Dificultad:",
    ["Todos", "Básico", "Intermedio", "Avanzado"]
)

filtro_caso = st.sidebar.selectbox(
    "Caso Gramatical:",
    ["Todos", "Nominativo", "Acusativo", "Dativo", "Genitivo"]
)

if "prev_diff" not in st.session_state:
    st.session_state.prev_diff = filtro_dificultad
if "prev_case" not in st.session_state:
    st.session_state.prev_case = filtro_caso

if st.session_state.prev_diff != filtro_dificultad or st.session_state.prev_case != filtro_caso:
    st.session_state.prev_diff = filtro_dificultad
    st.session_state.prev_case = filtro_caso
    st.session_state.ronda_num = 1
    st.session_state.current_card = None

# 4. Inicializar estados de la sesión
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False
if "ronda_num" not in st.session_state:
    st.session_state.ronda_num = 1

def fetch_next_card():
    query = supabase.table("german_flashcards").select("*")
    if filtro_dificultad != "Todos":
        query = query.eq("difficulty", filtro_dificultad)
    if filtro_caso != "Todos":
        query = query.eq("case", filtro_caso)
    
    response = query.execute()
    if response.data and len(response.data) > 0:
        st.session_state.current_card = random.choice(response.data)
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

if st.session_state.current_card is None:
    fetch_next_card()

# 5. Interfaz principal usando elementos 100% nativos estables
if st.session_state.current_card:
    card = st.session_state.current_card
    
    # Cabecera de la ronda
    st.subheader(f"🔫 RONDA {st.session_state.ronda_num} — Palabra: {card.get('word')}")
    
    # Etiquetas en formato texto simple pero limpio
    st.write(f"🔹 **Género:** {card.get('gender')} | **Caso:** {card.get('case')} | **Dificultad:** {card.get('difficulty')}")
    
    if card.get("subcategory"):
        st.caption(f"Categoría: {card.get('subcategory')}")
        
    st.markdown(f"**Situación:** *{card.get('situation')}*")
    
    # Destacamos la frase en español
    st.info(f"👉 **Frase a traducir:**\n### \"{card.get('spanish_phrase')}\"")
    
    # Botonera estándar
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ Revelar Solución", use_container_width=True):
            st.session_state.show_solution = True
            st.rerun()
    with col2:
        if st.button("🚀 Siguiente Tarjeta", type="primary", use_container_width=True):
            st.session_state.ronda_num += 1
            fetch_next_card()
            st.rerun()

    # Bloque de revelación
    if st.session_state.show_solution:
        st.success(f"### 🔊 Solución en Alemán:\n## `{card.get('german_solution')}`")
        
        explicacion_texto = card.get('explanation') or card.get('Explanation')
        if explicacion_texto:
            st.markdown(f"💡 **Explicación:** {explicacion_texto}")
            
        tip_texto = card.get('grammar_tip') or card.get('Grammar_tip')
        if tip_texto and str(tip_texto).strip().lower() != 'none':
            st.warning(f"🔑 **Grammar Tip:** {tip_texto}")
else:
    st.error("No hay tarjetas que coincidan con los filtros de la barra lateral.")
    if st.button("🔄 Resetear"):
        fetch_next_card()
        st.rerun()
