import streamlit as st
from supabase import create_client, Client
import random
import json
from datetime import datetime, date
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

# Estilos CSS estables inyectados mediante st.html
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
    .status-indicator {
        padding: 8px 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: 500;
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
    "Masculino": "#3b82f6",
    "Femenino": "#ec4899",
    "Neutro": "#10b981",
    "Plural": "#8b5cf6"
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
# 4. CACHÉ DE TARJETAS (OPTIMIZACIÓN)
# ============================================
@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_all_cards():
    """Obtiene todas las tarjetas de la base de datos con caché"""
    try:
        response = supabase.table("german_flashcards").select("*").execute()
        return response.data if response.data else []
    except:
        return []

# ============================================
# 5. SISTEMA DE RACHA (GAMIFICACIÓN)
# ============================================
def update_streak():
    """Actualiza la racha de estudio diaria"""
    today = date.today()
        
    if st.session_state.last_study_date is None:
        st.session_state.study_streak = 1
        st.session_state.last_study_date = today
        st.session_state.cards_today = 1
    elif st.session_state.last_study_date == today:
        st.session_state.cards_today += 1
    elif (today - st.session_state.last_study_date).days == 1:
        st.session_state.study_streak += 1
        st.session_state.last_study_date = today
        st.session_state.cards_today = 1
    else:
        st.session_state.study_streak = 1
        st.session_state.last_study_date = today
        st.session_state.cards_today = 1

# ============================================
# 6. INICIALIZAR ESTADOS DE SESIÓN
# ============================================
if "current_card" not in st.session_state:
    st.session_state.current_card = None
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False
if "ronda_num" not in st.session_state:
    st.session_state.ronda_num = 1
if "feedback_mensaje" not in st.session_state:
    st.session_state.feedback_mensaje = None

# Carga inicial de persistencia desde Supabase
if 'cards_studied' not in st.session_state:
    studied, mastered, difficult = load_progress_from_db()
    st.session_state.cards_studied = studied
    st.session_state.cards_mastered = mastered
    st.session_state.cards_difficult = difficult

# Sistema de racha
if 'last_study_date' not in st.session_state:
    st.session_state.last_study_date = None
if 'study_streak' not in st.session_state:
    st.session_state.study_streak = 0
if 'cards_today' not in st.session_state:
    st.session_state.cards_today = 0

# ============================================
# 7. SIDEBAR (FILTROS Y CONTADORES)
# ============================================
st.sidebar.title("🎯 Configurar Tiroteo")

filtro_dificultad = st.sidebar.selectbox(
    "Nivel de Dificultad:",
    ["Todos", "Básico", "Intermedio", "Avanzado"])

filtro_caso = st.sidebar.selectbox(
    "Caso Gramatical:",
    ["Todos", "Nominativo", "Acusativo", "Dativo", "Genitivo"])

filtro_modo = st.sidebar.selectbox(
    "Modo de Estudio:",
    ["Todas", "Solo pendientes", "Repasar difíciles", "Solo nuevas"],
    help="Solo pendientes: excluye dominadas | Repasar difíciles: solo las marcadas como difíciles | Solo nuevas: sin evaluar aún")

# Detectar cambios en filtros
if "prev_diff" not in st.session_state:
    st.session_state.prev_diff = filtro_dificultad
if "prev_case" not in st.session_state:
    st.session_state.prev_case = filtro_caso
if "prev_modo" not in st.session_state:
    st.session_state.prev_modo = filtro_modo

if (st.session_state.prev_diff != filtro_dificultad or 
    st.session_state.prev_case != filtro_caso or 
    st.session_state.prev_modo != filtro_modo):
    st.session_state.prev_diff = filtro_dificultad
    st.session_state.prev_case = filtro_caso
    st.session_state.prev_modo = filtro_modo
    st.session_state.ronda_num = 1
    st.session_state.current_card = None

# Progreso rápido
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Tu Progreso")
st.sidebar.metric("👍 Estudiadas", len(st.session_state.cards_studied))
st.sidebar.metric("✅ Dominadas", len(st.session_state.cards_mastered))
st.sidebar.metric("😰 Difíciles", len(st.session_state.cards_difficult))

# Sistema de rachas
st.sidebar.markdown("---")
st.sidebar.subheader("🔥 Racha de Estudio")
st.sidebar.metric("Días consecutivos", st.session_state.study_streak)
st.sidebar.metric("Tarjetas hoy", st.session_state.cards_today)

# Progreso hacia meta diaria
meta_diaria = 10
if st.session_state.cards_today > 0:
    progress_today = min(st.session_state.cards_today / meta_diaria, 1.0)
    st.sidebar.progress(progress_today, text=f"Meta diaria: {st.session_state.cards_today}/{meta_diaria}")

# ============================================
# 8. EXPORTAR/IMPORTAR PROGRESO
# ============================================
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Gestión de Progreso")

# Exportar
total_vistas = len(st.session_state.cards_studied) + len(st.session_state.cards_mastered) + len(st.session_state.cards_difficult)
progress_data = {
    'studied': list(st.session_state.cards_studied),
    'mastered': list(st.session_state.cards_mastered),
    'difficult': list(st.session_state.cards_difficult),
    'exported_at': datetime.now().isoformat(),
    'total_cards': total_vistas,
    'study_streak': st.session_state.study_streak,
    'cards_today': st.session_state.cards_today
}
json_str = json.dumps(progress_data, indent=2)

st.sidebar.download_button(
    label="📥 Exportar Progreso",
    data=json_str,
    file_name=f"progreso_aleman_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
    mime="application/json",
    use_container_width=True,
    type="secondary")

# Importar
uploaded_file = st.sidebar.file_uploader(
    "📤 Importar Progreso", 
    type=['json'],
    help="Sube un archivo JSON exportado previamente")

if uploaded_file:
    try:
        imported_data = json.load(uploaded_file)
                
        st.session_state.cards_studied = set(imported_data.get('studied', []))
        st.session_state.cards_mastered = set(imported_data.get('mastered', []))
        st.session_state.cards_difficult = set(imported_data.get('difficult', []))
                
        # Restaurar racha si existe
        if 'study_streak' in imported_data:
            st.session_state.study_streak = imported_data['study_streak']
        if 'cards_today' in imported_data:
            st.session_state.cards_today = imported_data['cards_today']
                
        # Guardar en DB
        for card_id in st.session_state.cards_studied:
            save_progress_to_db(card_id, 'studied')
        for card_id in st.session_state.cards_mastered:
            save_progress_to_db(card_id, 'mastered')
        for card_id in st.session_state.cards_difficult:
            save_progress_to_db(card_id, 'difficult')
                
        st.sidebar.success("✅ ¡Progreso importado correctamente!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ Error al importar: {e}")

# ============================================
# 9. BOTÓN DE RESET
# ============================================
st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Opciones Avanzadas"):
    st.write("**⚠️ Zona de peligro**")
    confirmar_reset = st.checkbox("Confirmar reinicio completo")
        
    if st.button(
        "🗑️ Reiniciar TODO el progreso",
        disabled=not confirmar_reset,
        use_container_width=True,
        type="secondary"
    ):
        try:
            # Limpiar DB
            supabase.table("user_progress").delete().eq("user_id", "default_user").execute()
                        
            # Limpiar session state
            st.session_state.cards_studied = set()
            st.session_state.cards_mastered = set()
            st.session_state.cards_difficult = set()
            st.session_state.ronda_num = 1
            st.session_state.current_card = None
            st.session_state.study_streak = 0
            st.session_state.cards_today = 0
            st.session_state.last_study_date = None
                        
            st.success("✅ Progreso reiniciado correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error al resetear: {e}")

# ============================================
# 10. LÓGICA DE CARGA OPTIMIZADA CON CACHÉ
# ============================================
def fetch_next_card():
    """Obtiene la siguiente tarjeta según filtros aplicados"""
    all_cards = get_all_cards()  
        
    if not all_cards:
        st.session_state.current_card = None
        return
        
    available_cards = all_cards
        
    if filtro_dificultad != "Todos":
        available_cards = [c for c in available_cards if c.get('difficulty') == filtro_dificultad]
    if filtro_caso != "Todos":
        available_cards = [c for c in available_cards if c.get('case') == filtro_caso]
        
    if filtro_modo == "Solo pendientes":
        available_cards = [c for c in available_cards if c['id'] not in st.session_state.cards_mastered]
    elif filtro_modo == "Repasar difíciles":
        difficult_cards = [c for c in available_cards if c['id'] in st.session_state.cards_difficult]
        if difficult_cards:
            available_cards = difficult_cards
        else:
            available_cards = []
    elif filtro_modo == "Solo nuevas":
        available_cards = [
            c for c in available_cards 
            if c['id'] not in st.session_state.cards_studied
            and c['id'] not in st.session_state.cards_mastered
            and c['id'] not in st.session_state.cards_difficult
        ]
        
    if available_cards:
        st.session_state.current_card = random.choice(available_cards)
        st.session_state.show_solution = False
    else:
        st.session_state.current_card = None

if st.session_state.current_card is None:
    fetch_next_card()

# ============================================
# 11. INTERFAZ PRINCIPAL CON TABS
# ============================================
tab1, tab2 = st.tabs(["🔫 Tiroteo", "📊 Estadísticas Avanzadas"])

# --------------------------------------------------------
# PESTAÑA 1: EL JUEGO DE LAS TARJETAS
# --------------------------------------------------------
with tab1:
    if st.session_state.current_card:
        card = st.session_state.current_card
        card_id = card.get('id')
        genero = card.get('gender', 'Masculino')
        color_genero = GENERO_COLORES.get(genero, '#6b7280')
                
        # Muestra el cartel fijo del resultado anterior si existe
        if st.session_state.feedback_mensaje:
            msg = st.session_state.feedback_mensaje
            if msg["tipo"] == "success":
                st.success(msg["texto"])
            elif msg["tipo"] == "error":
                st.error(msg["texto"])
            else:
                st.info(msg["texto"])
            st.session_state.feedback_mensaje = None
            
        st.subheader(f"🔫 RONDA {st.session_state.ronda_num} — Palabra: {card.get('word')}")
                
        # Badges de género, caso y dificultad
        st.html(f"""
            <div class="badge-container">
                <span class="badge" style="background-color: {color_genero};">{genero}</span>
                <span class="badge" style="background-color: #4b5563;">{card.get('case')}</span>
                <span class="badge" style="background-color: #1f2937;">{card.get('difficulty')}</span>
            </div>
        """)
                
        # INDICADOR DE ESTADO PREVIO
        if card_id in st.session_state.cards_mastered:
            st.html("""
                <div class="status-indicator" style="background-color: #d1fae5; color: #065f46; border-left: 4px solid #10b981;">
                    ✅ Ya dominaste esta tarjeta anteriormente
                </div>
            """)
        elif card_id in st.session_state.cards_studied:
            st.html("""
                <div class="status-indicator" style="background-color: #dbeafe; color: #1e40af; border-left: 4px solid #3b82f6;">
                    👍 Ya estudiaste esta tarjeta
                </div>
            """)
        elif card_id in st.session_state.cards_difficult:
            st.html("""
                <div class="status-indicator" style="background-color: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444;">
                    😰 Marcaste esta tarjeta como difícil
                </div>
            """)
                
        # Bloque dinámico: Muestra Español o Alemán manteniendo el formato idéntico
        if st.session_state.show_solution:
            st.html(f"""
                <div class="phrase-box" style="border-left: 4px solid {color_genero};">
                    <span style="color: gray; font-size: 14px; font-weight: normal; display: block; margin-bottom: 4px;">Alemán:</span>
                    "{card.get('german_solution')}"
                </div>
            """)
        else:
            st.html(f"""
                <div class="phrase-box" style="border-left: 4px solid {color_genero};">
                    <span style="color: gray; font-size: 14px; font-weight: normal; display: block; margin-bottom: 4px;">Frase a traducir:</span>
                    "{card.get('spanish_phrase')}"
                </div>
            """)
                
        # FILA 1: Botones de Acción Principal
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
                
        # FILA 2: Bloque de revelación (Explicación + Botones de Feedback)
        if st.session_state.show_solution:
            explicacion_texto = card.get('explanation') or card.get('Explanation')
            if explicacion_texto:
                st.info(f"💡 **Explicación:** {explicacion_texto}")
                        
            tip_texto = card.get('grammar_tip') or card.get('Grammar_tip')
            if tip_texto and str(tip_texto).strip().lower() != 'none':
                st.warning(f"🔑 **Grammar Tip:** {tip_texto}")
                        
            st.markdown("---")
                        
            fb_col1, fb_col2, fb_col3 = st.columns(3)
                        
            with fb_col1:
                if st.button("😰 Mal", key=f"diff_{card_id}", use_container_width=True):
                    st.session_state.cards_difficult.add(card_id)
                    st.session_state.cards_studied.discard(card_id)
                    st.session_state.cards_mastered.discard(card_id)
                    save_progress_to_db(card_id, 'difficult')
                    update_streak()
                    
                    st.session_state.feedback_mensaje = {"texto": "😰 Tarjeta anterior marcada como MAL. ¡A por otra!", "tipo": "error"}
                    
                    st.session_state.ronda_num += 1
                    st.session_state.show_solution = False
                    fetch_next_card()
                    st.rerun()
                        
            with fb_col2:
                if st.button("👍 Bien", key=f"ok_{card_id}", use_container_width=True):
                    st.session_state.cards_studied.add(card_id)
                    st.session_state.cards_difficult.discard(card_id)
                    st.session_state.cards_mastered.discard(card_id)
                    save_progress_to_db(card_id, 'studied')
                    update_streak()
                    
                    st.session_state.feedback_mensaje = {"texto": "👍 ¡Bien hecho! Tarjeta anterior registrada.", "tipo": "info"}
                    
                    st.session_state.ronda_num += 1
                    st.session_state.show_solution = False
                    fetch_next_card()
                    st.rerun()
                        
            with fb_col3:
                if st.button("✅ Dominada", key=f"master_{card_id}", type="secondary", use_container_width=True):
                    st.session_state.cards_mastered.add(card_id)
                    st.session_state.cards_studied.discard(card_id)
                    st.session_state.cards_difficult.discard(card_id)
                    save_progress_to_db(card_id, 'mastered')
                    update_streak()
                    
                    st.session_state.feedback_mensaje = {"texto": "🏆 ¡Espectacular! Tarjeta anterior DOMINADA por completo.", "tipo": "success"}
                    
                    st.session_state.ronda_num += 1
                    st.session_state.show_solution = False
                    fetch_next_card()
                    st.rerun()
    else:
        st.warning("⚠️ No hay tarjetas disponibles con los filtros aplicados.")
                
        if filtro_modo == "Repasar difíciles" and len(st.session_state.cards_difficult) == 0:
            st.info("💡 No tienes tarjetas marcadas como difíciles. ¡Marca algunas primero!")
        elif filtro_modo == "Solo nuevas":
            st.info("💡 Has visto todas las tarjetas nuevas con estos filtros. ¡Excelente progreso!")
        elif filtro_modo == "Solo pendientes":
            st.success("🎉 ¡Has dominado todas las tarjetas con estos filtros!")
                
        if st.button("🔄 Cambiar filtros", use_container_width=True):
            st.session_state.current_card = None
            st.rerun()

# --------------------------------------------------------
# PESTAÑA 2: ESTADÍSTICAS AVANZADAS
# --------------------------------------------------------
with tab2:
    st.header("📊 Tus Estadísticas de Estudio")
        
    all_cards_count = len(get_all_cards())
        
    cards_studied = len(st.session_state.cards_studied)
    cards_mastered = len(st.session_state.cards_mastered)
    cards_difficult = len(st.session_state.cards_difficult)
    total_vistas = cards_studied + cards_mastered + cards_difficult
    cards_nuevas = max(0, all_cards_count - total_vistas)
        
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📚 Total Vistas", f"{total_vistas}/{all_cards_count}")
    col2.metric("✅ Dominadas", cards_mastered)
    col3.metric("👍 En Progreso", cards_studied)
    col4.metric("😰 Difíciles", cards_difficult)
        
    st.markdown("---")
        
    grafico_col1, grafico_col2 = st.columns(2)
        
    with grafico_col1:
        st.subheader("🎯 Distribución Global")
                
        try:
            labels = ['⏳ Nuevas', '👍 En Progreso', '😰 Difíciles', '✅ Dominadas']
            values = [cards_nuevas, cards_studied, cards_difficult, cards_mastered]
            colors = ['#9ca3af', '#3b82f6', '#ef4444', '#10b981']
                        
            fig_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker=dict(colors=colors),
                textinfo='percent+value',
                textposition='outside'
            )])
                        
            fig_pie.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                height=350,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
            )
                        
            st.plotly_chart(fig_pie, use_container_width=True)
        except Exception as e:
            st.error(f"Error al cargar gráfico: {e}")
        
    with grafico_col2:
        st.subheader("🧠 Dominio por Caso")
                
        try:
            all_cards_data = get_all_cards()
                        
            if all_cards_data:
                df_cards = pd.DataFrame(all_cards_data)
                                
                def get_status(card_id):
                    if card_id in st.session_state.cards_mastered: return 'Dominada'
                    if card_id in st.session_state.cards_difficult: return 'Difícil'
                    if card_id in st.session_state.cards_studied: return 'En Progreso'
                    return 'Nueva'
                                
                df_cards['Estado'] = df_cards['id'].apply(get_status)
                                
                df_grouped = df_cards.groupby(['case', 'Estado']).size().reset_index(name='Cantidad')
                df_pivot = df_grouped.pivot(index='case', columns='Estado', values='Cantidad').fillna(0)
                                
                for col in ['Nueva', 'En Progreso', 'Difícil', 'Dominada']:
                    if col not in df_pivot.columns:
                        df_pivot[col] = 0
                                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(name='✅ Dominada', x=df_pivot.index, y=df_pivot['Dominada'], marker_color='#10b981'))
                fig_bar.add_trace(go.Bar(name='👍 En Progreso', x=df_pivot.index, y=df_pivot['En Progreso'], marker_color='#3b82f6'))
                fig_bar.add_trace(go.Bar(name='😰 Difícil', x=df_pivot.index, y=df_pivot['Difícil'], marker_color='#ef4444'))
                fig_bar.add_trace(go.Bar(name='⏳ Nueva', x=df_pivot.index, y=df_pivot['Nueva'], marker_color='#9ca3af'))
                                
                fig_bar.update_layout(
                    barmode='stack',
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=350,
                    xaxis_title="Caso Gramatical",
                    yaxis_title="Tarjetas",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                                
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No hay datos disponibles")
        except Exception as e:
            st.warning(f"Estudia algunas tarjetas para ver estadísticas detalladas. ({e})")
        
    st.markdown("---")
    st.subheader("📋 Detalle por Caso Gramatical")
        
    try:
        all_cards_data = get_all_cards()
        if all_cards_data:
            df_cards = pd.DataFrame(all_cards_data)
                        
            casos = ["Nominativo", "Acusativo", "Dativo", "Genitivo"]
            stats_por_caso = []
                        
            for caso in casos:
                cards_caso = df_cards[df_cards['case'] == caso]
                                
                if len(cards_caso) > 0:
                    card_ids_caso = set(cards_caso['id'].values)
                                        
                    dominadas_caso = len(card_ids_caso & st.session_state.cards_mastered)
                    estudiadas_caso = len(card_ids_caso & st.session_state.cards_studied)
                    dificiles_caso = len(card_ids_caso & st.session_state.cards_difficult)
                    total_caso = len(card_ids_caso)
                    pendientes_caso = total_caso - dominadas_caso - estudiadas_caso - dificiles_caso
                    porcentaje = round((dominadas_caso / total_caso * 100), 1) if total_caso > 0 else 0
                                        
                    stats_por_caso.append({
                        'Caso': caso,
                        'Total': total_caso,
                        '✅ Dominadas': dominadas_caso,
                        '👍 Estudiadas': estudiadas_caso,
                        '😰 Difíciles': dificiles_caso,
                        '⏳ Pendientes': pendientes_caso,
                        '% Dominio': f"{porcentaje}%"
                    })
                        
            if stats_por_caso:
                df_stats = pd.DataFrame(stats_por_caso)
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error al generar tabla: {e}")
        
    st.markdown("---")
    st.subheader("🎨 Progreso por Género")
        
    try:
        all_cards_data = get_all_cards()
        if all_cards_data:
            df_cards = pd.DataFrame(all_cards_data)
                        
            generos = ["Masculino", "Femenino", "Neutro", "Plural"]
            stats_por_genero = []
                        
            for genero in generos:
                cards_genero = df_cards[df_cards['gender'] == genero]
                                
                if len(cards_genero) > 0:
                    card_ids_genero = set(cards_genero['id'].values)
                                        
                    dominadas_gen = len(card_ids_genero & st.session_state.cards_mastered)
                    total_gen = len(card_ids_genero)
                    porcentaje_gen = round((dominadas_gen / total_gen * 100), 1) if total_gen > 0 else 0
                                        
                    stats_por_genero.append({
                        'Género': genero,
                        'Total': total_gen,
                        'Dominadas': dominadas_gen,
                        '% Completado': porcentaje_gen
                    })
                        
            if stats_por_genero:
                df_genero = pd.DataFrame(stats_por_genero)
                                
                fig_gender = go.Figure()
                                
                fig_gender.add_trace(go.Bar(
                    y=df_genero['Género'],
                    x=df_genero['% Completado'],
                    orientation='h',
                    marker=dict(color=['#3b82f6', '#ec4899', '#10b981', '#8b5cf6']),
                    text=df_genero['% Completado'].apply(lambda x: f'{x}%'),
                    textposition='outside'
                ))
                                
                fig_gender.update_layout(
                    height=300,
                    xaxis_title="% Dominadas",
                    xaxis_range=[0, 100],
                    yaxis_title="",
                    showlegend=False,
                    margin=dict(t=20, b=20, l=10, r=50)
                )
                                
                st.plotly_chart(fig_gender, use_container_width=True)
                st.dataframe(df_genero, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error al cargar progreso por género: {e}")
        
    st.markdown("---")
    st.subheader("💡 Recomendaciones Personalizadas")
        
    if len(st.session_state.cards_difficult) > 10:
        st.warning(f"⚠️ Tienes **{len(st.session_state.cards_difficult)} tarjetas** marcadas como difíciles. Considera usar el modo **'Repasar difíciles'**.")
    if len(st.session_state.cards_mastered) > 50:
        st.success(f"🎉 ¡Excelente! Has dominado **{len(st.session_state.cards_mastered)} tarjetas**. ¡Sigue así!")
    if total_vistas < 20:
        st.info("📚 ¡Empecemos! Intenta estudiar al menos **20 tarjetas** para tener estadísticas más precisas.")
    if st.session_state.study_streak >= 3:
        st.success(f"🔥 ¡Racha de **{st.session_state.study_streak} días**! ¡No la rompas!")
        
    try:
        all_cards_data = get_all_cards()
        if all_cards_data and total_vistas > 10:
            df_cards = pd.DataFrame(all_cards_data)
                        
            peor_caso = None
            peor_porcentaje = 100
                        
            for caso in ["Nominativo", "Acusativo", "Dativo", "Genitivo"]:
                cards_caso = df_cards[df_cards['case'] == caso]
                if len(cards_caso) > 0:
                    card_ids_caso = set(cards_caso['id'].values)
                    dominadas = len(card_ids_caso & st.session_state.cards_mastered)
                    porcentaje = (dominadas / len(card_ids_caso) * 100) if len(card_ids_caso) > 0 else 0
                                        
                    if porcentaje < peor_porcentaje:
                        peor_porcentaje = porcentaje
                        peor_caso = caso
                        
            if peor_caso and peor_porcentaje < 50:
                st.info(f"📖 Tu caso con menor dominio es **{peor_caso}** ({peor_porcentaje:.1f}%). ¡Enfócate en él!")
    except:
        pass
