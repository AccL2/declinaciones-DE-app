import streamlit as st
from supabase import create_client, Client
import random
import json
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd

# ============================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS CSS
# ============================================
st.set_page_config(
    page_title="Tiroteo de Alemán", 
    page_icon="🔫", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# Estilos CSS estables inyectados mediante st.html (Vuelven los colores)
st.html("""
    <style>
    .badge-container {
        display: flex;
        gap: 8px;
        margin-top: 5px;
        margin-bottom: 15px;
    }
    .badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        color: white;
        text-transform: uppercase;
    }
    .phrase-box {
        font-size: 24px; 
        font-weight: bold; 
        margin-top: 15px; 
        margin-bottom: 20px; 
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

GENERO_COLORES = {
    "Masculino": "#3b82f6",  # Azul eléctrico
    "Femenino": "#ec4899",   # Rosa vibrante
    "Neutro": "#10b981",     # Verde esmeralda
    "Plural": "#8b5cf6"      # Morado neón
}

# ============================================
# 3. FUNCIONES DE PERSISTENCIA (BASE DE DATOS)
# ============================================
def load_progress_from_db():
    """Carga el progreso guardado en Supabase"""
    try:
        response = supabase.table("user_progress").select("*").eq("user_id", "default_user").execute()
                
        studied = set()
        mastered = set()
        difficult = set()
                
        for row in response.data:
            card_id = row['card_id']
            status = row['status']
                        
            if status == 'studied':
                studied.add(card_id)
            elif status == 'mastered':
                mastered.add(card_id)
            elif status == 'difficult':
                difficult.add(card_id)
                
        return studied, mastered, difficult
    except:
        return set(), set(), set()

def save_progress_to_db(card_id, status):
    """Guarda o actualiza el progreso de una tarjeta específica"""
    try:
        supabase.table("user_progress").delete().eq("user_id", "default_user").eq("card_id", card_id).execute()
        supabase.table("user_progress").insert({
            "user_id": "default_user",
            "card_id": card_id,
            "status": status
        }).execute()
    except Exception as e:
        st.error(f"Error guardando progreso: {e}")

# ============================================
# 4. INICIALIZAR ESTADOS DE SESIÓN
# ============================================
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False
if "ronda_num" not in st.session_state:
    st.session_state.ronda_num = 1

# Carga inicial de persistencia desde Supabase
if 'cards_studied' not in st.session_state:
    studied, mastered, difficult = load_progress_from_db()
    st.session_state.cards_studied = studied
    st.session_state.cards_mastered = mastered
    st.session_state.cards_difficult = difficult

# ============================================
# 5. SIDEBAR (FILTROS Y CONTADORES RÁPIDOS)
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

filtro_modo = st.sidebar.selectbox(
    "Modo de Estudio:",
    ["Todas", "Solo pendientes", "Repasar difíciles", "Solo nuevas"]
)

# Guardar filtros previos para detectar cambios
if "prev_diff" not in st.session_state:
    st.session_state.prev_diff = filtro_dificultad
if "prev_case" not in st.session_state:
    st.session_state.prev_case = filtro_caso
if "prev_modo" not in st.session_state:
    st.session_state.prev_modo = filtro_modo

# Si cambias un filtro, reiniciamos la ronda y forzamos nueva tarjeta
if (st.session_state.prev_diff != filtro_dificultad or 
    st.session_state.prev_case != filtro_caso or 
    st.session_state.prev_modo != filtro_modo):
    st.session_state.prev_diff = filtro_dificultad
    st.session_state.prev_case = filtro_caso
    st.session_state.prev_modo = filtro_modo
    st.session_state.ronda_num = 1
    st.session_state.current_card = None

# Cuadro visual de progreso rápido en el lateral
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Tu Progreso Rápido")
st.sidebar.metric("👍 Estudiadas (Bien)", len(st.session_state.cards_studied))
st.sidebar.metric("✅ Dominadas", len(st.session_state.cards_mastered))
st.sidebar.metric("😰 Difíciles", len(st.session_state.cards_difficult))
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Resetear Todo el Progreso", type="secondary", use_container_width=True):
    try:
        # Borra todo el progreso del usuario en Supabase
        supabase.table("user_progress").delete().eq("user_id", "default_user").execute()
        
        # Limpia los contadores en la pantalla actual
        st.session_state.cards_studied = set()
        st.session_state.cards_mastered = set()
        st.session_state.cards_difficult = set()
        st.session_state.ronda_num = 1
        st.session_state.current_card = None
        
        st.toast("Progress reset successfully!", icon="♻️")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error al resetear: {e}")

# ============================================
# 6. LÓGICA DE CARGA INTELIGENTE FILTRADA
# ============================================
def fetch_next_card():
    query = supabase.table("german_flashcards").select("*")
        
    if filtro_dificultad != "Todos":
        query = query.eq("difficulty", filtro_dificultad)
    if filtro_caso != "Todos":
        query = query.eq("case", filtro_caso)
        
    response = query.execute()
        
    if response.data and len(response.data) > 0:
        available_cards = response.data
                
        # Filtros según el Modo de Estudio seleccionado
        if filtro_modo == "Solo pendientes":
            available_cards = [c for c in available_cards if c['id'] not in st.session_state.cards_mastered]
        elif filtro_modo == "Repasar difíciles":
            available_cards = [c for c in available_cards if c['id'] in st.session_state.cards_difficult]
        elif filtro_modo == "Solo nuevas":
            available_cards = [c for c in available_cards if 
                               c['id'] not in st.session_state.cards_studied and 
                               c['id'] not in st.session_state.cards_mastered and 
                               c['id'] not in st.session_state.cards_difficult]
                
        # Si quedan tarjetas válidas tras los filtros, elegimos una al azar
        if available_cards:
            st.session_state.current_card = random.choice(available_cards)
            st.session_state.show_solution = False
        else:
            st.session_state.current_card = None
    else:
        st.session_state.current_card = None

if st.session_state.current_card is None:
    fetch_next_card()

# ============================================
# 7. INTERFAZ PRINCIPAL ORGANIZADA EN TABS
# ============================================
tab1, tab2 = st.tabs(["🔫 Tiroteo", "📊 Estadísticas Avanzadas"])

# --------------------------------------------------------
# PESTAÑA 1: EL JUEGO DE LAS TARJETAS (TIROTEO)
# --------------------------------------------------------
with tab1:
    if st.session_state.current_card:
        card = st.session_state.current_card
        card_id = card.get('id')
        genero = card.get('gender', 'Masculino')
        color_genero = GENERO_COLORES.get(genero, '#6b7280')
                
        st.subheader(f"🔫 RONDA {st.session_state.ronda_num} — Palabra: {card.get('word')}")
                
        # Renderizado de las etiquetas neón
        st.html(f"""
            <div class="badge-container">
                <span class="badge" style="background-color: {color_genero};">{genero}</span>
                <span class="badge" style="background-color: #4b5563;">{card.get('case')}</span>
                <span class="badge" style="background-color: #1f2937;">{card.get('difficulty')}</span>
            </div>
        """)
                
        if card.get("subcategory"):
            st.caption(f"Categoría: {card.get('subcategory')}")
                    
        st.markdown(f"**Situación:** *{card.get('situation')}*")
                
        # Cuadro de la frase con borde de color dinámico
        st.html(f"""
            <div class="phrase-box" style="border-left: 4px solid {color_genero};">
                <span style="color: gray; font-size: 14px; font-weight: normal; display: block; margin-bottom: 4px;">Frase a traducir:</span>
                "{card.get('spanish_phrase')}"
            </div>
        """)
                
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👁️ Revelar Solución", use_container_width=True):
                st.session_state.show_solution = True
                st.rerun()
        with col2:
            if st.button("🚀 Saltar / Siguiente", type="secondary", use_container_width=True):
                st.session_state.ronda_num += 1
                fetch_next_card()
                st.rerun()
                
        # Bloque expansivo de revelación
        if st.session_state.show_solution:
            st.success(f"### 🔊 Solución en Alemán:\n## `{card.get('german_solution')}`")
                        
            explicacion_texto = card.get('explanation') or card.get('Explanation')
            if explicacion_texto:
                st.info(f"💡 **Explicación:** {explicacion_texto}")
                            
            tip_texto = card.get('grammar_tip') or card.get('Grammar_tip')
            if tip_texto and str(tip_texto).strip().lower() != 'none':
                st.warning(f"🔑 **Grammar Tip:** {tip_texto}")
                            
            st.markdown("---")
            st.markdown("### ¿Cómo te ha ido con esta tarjeta?")
                        
            fb_col1, fb_col2, fb_col3 = st.columns(3)
                        
            with fb_col1:
                if st.button("😰 Difícil", key=f"diff_{card_id}", use_container_width=True):
                    st.session_state.cards_difficult.add(card_id)
                    st.session_state.cards_studied.discard(card_id)
                    st.session_state.cards_mastered.discard(card_id)
                    save_progress_to_db(card_id, 'difficult')
                    st.toast("😰 Marcada como difícil", icon="📌")
                    st.session_state.ronda_num += 1
                    fetch_next_card()
                    st.rerun()
                                
            with fb_col2:
                if st.button("👍 Bien", key=f"ok_{card_id}", use_container_width=True):
                    st.session_state.cards_studied.add(card_id)
                    st.session_state.cards_difficult.discard(card_id)
                    st.session_state.cards_mastered.discard(card_id)
                    save_progress_to_db(card_id, 'studied')
                    st.toast("👍 ¡Bien hecho!", icon="✨")
                    st.session_state.ronda_num += 1
                    fetch_next_card()
                    st.rerun()
                                
            with fb_col3:
                if st.button("✅ Dominada", key=f"master_{card_id}", type="primary", use_container_width=True):
                    st.session_state.cards_mastered.add(card_id)
                    st.session_state.cards_studied.discard(card_id)
                    st.session_state.cards_difficult.discard(card_id)
                    save_progress_to_db(card_id, 'mastered')
                    st.toast("🎉 ¡Dominada!", icon="🏆")
                    st.session_state.ronda_num += 1
                    fetch_next_card()
                    st.rerun()
    else:
        st.error("No hay tarjetas disponibles con los filtros aplicados.")
        if st.button("🔄 Resetear filtros de estudio"):
            st.session_state.current_card = None
            st.rerun()

# --------------------------------------------------------
# PESTAÑA 2: CUADRO DE MANDOS Y GRÁFICOS DE ESTADÍSTICAS
# --------------------------------------------------------
with tab2:
    st.header("📊 Tus Estadísticas de Estudio")
    
    total_cards_db = 180  # Tamaño real de tu base de datos
    cards_studied = len(st.session_state.cards_studied)
    cards_mastered = len(st.session_state.cards_mastered)
    cards_difficult = len(st.session_state.cards_difficult)
    total_vistas = cards_studied + cards_mastered + cards_difficult
    cards_nuevas = max(0, total_cards_db - total_vistas)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Vistas", f"{total_vistas}/{total_cards_db}")
    col2.metric("✅ Dominadas", cards_mastered)
    col3.metric("👍 En Progreso", cards_studied)
    col4.metric("😰 Difíciles", cards_difficult)
    
    st.markdown("---")
    
    grafico_col1, grafico_col2 = st.columns(2)
    
    # GRÁFICO 1: TARTA DE DISTRIBUCIÓN GENERAL
    with grafico_col1:
        st.subheader("🎯 Distribución Global")
        
        labels = ['Nuevas', 'En Progreso (Bien)', 'Difíciles', 'Dominadas']
        values = [cards_nuevas, cards_studied, cards_difficult, cards_mastered]
        colors = ['#4b5563', '#3b82f6', '#ef4444', '#10b981']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=labels, 
            values=values, 
            hole=.4,
            marker=dict(colors=colors),
            textinfo='percent+value'
        )])
        
        fig_pie.update_layout(
            margin=dict(t=20, b=20, l=10, r=10),
            height=300,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # GRÁFICO 2: RENDIMIENTO POR CASO GRAMATICAL (BARRAS APILADAS)
    with grafico_col2:
        st.subheader("🧠 Dominio por Caso Gramatical")
        
        try:
            res = supabase.table("german_flashcards").select("id", "case").execute()
            df_cards = pd.DataFrame(res.data)
            
            if not df_cards.empty:
                # Clasificar cada tarjeta según el session_state reactivo
                def buscar_estado(card_id):
                    if card_id in st.session_state.cards_mastered: return 'Dominada'
                    if card_id in st.session_state.cards_difficult: return 'Difícil'
                    if card_id in st.session_state.cards_studied: return 'En Progreso'
                    return 'Nueva'
                
                df_cards['Estado'] = df_cards['id'].apply(buscar_estado)
                
                # Agrupar y pivotar para construir el gráfico de barras apiladas
                df_grouped = df_cards.groupby(['case', 'Estado']).size().reset_index(name='Cantidad')
                df_pivot = df_grouped.pivot(index='case', columns='Estado', values='Cantidad').fillna(0)
                
                for col in ['Nueva', 'En Progreso', 'Difícil', 'Dominada']:
                    if col not in df_pivot.columns:
                        df_pivot[col] = 0
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(name='Dominada', x=df_pivot.index, y=df_pivot['Dominada'], marker_color='#10b981'))
                fig_bar.add_trace(go.Bar(name='En Progreso', x=df_pivot.index, y=df_pivot['En Progreso'], marker_color='#3b82f6'))
                fig_bar.add_trace(go.Bar(name='Difícil', x=df_pivot.index, y=df_pivot['Difícil'], marker_color='#ef4444'))
                fig_bar.add_trace(go.Bar(name='Nueva', x=df_pivot.index, y=df_pivot['Nueva'], marker_color='#4b5563'))
                
                fig_bar.update_layout(
                    barmode='stack',
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=300,
                    xaxis_title="Casos Gramaticales",
                    yaxis_title="Tarjetas",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No hay datos disponibles en la tabla de tarjetas.")
        except Exception as e:
            st.warning("Vota algunas tarjetas primero para poder calcular tu mapa de rendimiento.")
