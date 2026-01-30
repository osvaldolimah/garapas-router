import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from folium.features import DivIcon
import requests

# --- 1. FUNÇÕES DE INTELIGÊNCIA ---

def fast_haversine(lat1, lon1, lat2, lon2):
    """Calcula a distância matemática básica entre dois pontos."""
    p = np.pi/180
    a = 0.5 - np.cos((lat2-lat1)*p)/2 + np.cos(lat1*p) * np.cos(lat2*p) * (1-np.cos((lon2-lon1)*p))/2
    return 12742 * np.arcsin(np.sqrt(a))

def get_road_route_batch(points):
    """Gera o trajeto real seguindo as ruas através do motor OSRM."""
    if len(points) < 2: return points
    coords_str = ";".join([f"{p[1]},{p[0]}" for p in points])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            coords = r.json()['routes'][0]['geometry']['coordinates']
            return [[c[1], c[0]] for c in coords]
    except:
        pass
    return points

# --- 2. DESIGN SYSTEM (UX GARAPAS ROUTER) ---

st.set_page_config(page_title="Garapas Router", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .delivery-card { 
        border-radius: 16px; padding: 22px; margin-bottom: 12px; 
        background-color: white; border-left: 10px solid #FF4B4B;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .next-target { border-left: 10px solid #007BFF !important; background-color: #f0f7ff !important; }
    .address-header { font-size: 24px !important; font-weight: 800 !important; color: #1a1a1a; line-height: 1.1; }
    .bairro-sub { font-size: 16px !important; color: #555; font-weight: 500; margin-bottom: 10px;}
    .stTextInput input {
        background-color: #1e1e1e !important; color: #39FF14 !important;
        font-family: 'Roboto Mono', monospace; font-size: 20px !important; text-align: center;
    }
    .stButton button { height: 55px !important; border-radius: 12px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Garapas Router | Inteligência Logística")

# --- 3. INICIALIZAÇÃO DA MEMÓRIA ---

if 'df_final' not in st.session_state: st.session_state['df_final'] = None
if 'road_path' not in st.session_state: st.session_state['road_path'] = []
if 'entregues' not in st.session_state: st.session_state['entregues'] = set()
if 'custom_sequences' not in st.session_state: st.session_state['custom_sequences'] = {}
if 'versao_lista' not in st.session_state: st.session_state['versao_lista'] = 0

# --- 4. FLUXO DE GERAÇÃO DE ROTA ---

with st.expander("📂 Importar Planilha de Entregas", expanded=(st.session_state['df_final'] is None)):
    uploaded_file = st.file_uploader("", type=['xlsx'])
    if uploaded_file:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        df_clean = df_raw.dropna(subset=['LATITUDE', 'LONGITUDE'])

        if st.button("🚀 OTIMIZAR E CRIAR ROTA GARAPAS", use_container_width=True):
            with st.spinner("Garapas Router calculando melhor ordem..."):
                df_temp = df_clean.copy().reset_index()
                rota = []
                p_atual = df_temp.iloc[0]
                rota.append(p_atual)
                df_temp = df_temp.drop(df_temp.index[0])
                
                while not df_temp.empty:
                    dists = fast_haversine(p_atual['LATITUDE'], p_atual['LONGITUDE'], 
                                           df_temp['LATITUDE'].values, df_temp['LONGITUDE'].values)
                    idx = np.argmin(dists)
                    p_atual = df_temp.iloc[idx]
                    rota.append(p_atual)
                    df_temp = df_temp.drop(df_temp.index[idx])
                
                final_df = pd.DataFrame(rota).reset_index(drop=True)
                final_df['ORDEM_PARADA'] = range(1, len(final_df) + 1)
                st.session_state['df_final'] = final_df
                
            with st.spinner("Desenhando traçado rodoviário..."):
                coords = final_df[['LATITUDE', 'LONGITUDE']].values.tolist()
                st.session_state['road_path'] = get_road_route_batch(coords)
            
            st.session_state['entregues'] = set()
            st.session_state['custom_sequences'] = {}
            st.session_state['versao_lista'] += 1
            st.rerun()

# --- 5. INTERFACE DO ESTRATEGISTA ---

if st.session_state['df_final'] is not None:
    df_res = st.session_state['df_final']
    entregues_list = st.session_state['entregues']
    restantes_indices = [i for i in range(len(df_res)) if i not in entregues_list]

    # Métricas Operacionais
    km_vovo = 0.0
    for k in range(len(restantes_indices) - 1):
        p1 = df_res.iloc[restantes_indices[k]]
        p2 = df_res.iloc[restantes_indices[k+1]]
        km_vovo += fast_haversine(p1['LATITUDE'], p1['LONGITUDE'], p2['LATITUDE'], p2['LONGITUDE'])
    
    col_met1, col_met2, col_btn = st.columns([1, 1, 1.2])
    with col_met1: st.metric("📦 Restantes", len(restantes_indices))
    with col_met2: st.metric("🛤️ KM Rodoviário (Est.)", f"{km_vovo * 1.3:.1f} km")
    with col_btn:
        st.write("")
        if st.button("🗑️ LIMPAR CONCLUÍDAS", use_container_width=True):
            if restantes_indices:
                novo_df = df_res.iloc[restantes_indices].reset_index(drop=True)
                novo_df['ORDEM_PARADA'] = range(1, len(novo_df) + 1)
                novas_notas = {nova: st.session_state['custom_sequences'].get(antiga, "") 
                               for nova, antiga in enumerate(restantes_indices)}
                
                st.session_state['df_final'] = novo_df
                st.session_state['custom_sequences'] = novas_notas
                st.session_state['entregues'] = set()
                with st.spinner("Atualizando Garapas Router..."):
                    coords = novo_df[['LATITUDE', 'LONGITUDE']].values.tolist()
                    st.session_state['road_path'] = get_road_route_batch(coords)
                st.session_state['versao_lista'] += 1
                st.rerun()

    # MAPA COM IDs SEQUENCIAIS
    st.subheader("📍 Mapa de Apoio")
    m = folium.Map(location=[df_res['LATITUDE'].mean(), df_res['LONGITUDE'].mean()], zoom_start=13, tiles="cartodbpositron")
    
    if st.session_state['road_path']:
        folium.PolyLine(st.session_state['road_path'], color="#007BFF", weight=5, opacity=0.7).add_to(m)

    for i, row in df_res.iterrows():
        foi = i in entregues_list
        cor = "#28A745" if foi else ("#007BFF" if (restantes_indices and i == restantes_indices[0]) else "#FF4B4B")
        id_p = int(row['ORDEM_PARADA'])
        
        icon_html = f'''<div style="background-color: {cor}; border: 3px solid white; border-radius: 50%; 
                        width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; 
                        color: white; font-weight: bold; font-size: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">{id_p}</div>'''
        folium.Marker(location=[row['LATITUDE'], row['LONGITUDE']],
                      icon=DivIcon(icon_size=(32,32), icon_anchor=(16,16), html=icon_html)).add_to(m)
    st_folium(m, width=1400, height=450, key=f"map_v{st.session_state['versao_lista']}")

    # LISTA DE ENTREGAS
    st.markdown("---")
    busca = st.text_input("🔍 FILTRAR RUA OU SEQUENCE").upper()

    for i, row in df_res.iterrows():
        rua, bairro = str(row.get('DESTINATION ADDRESS', '---')), str(row.get('BAIRRO', ''))
        seq_v = st.session_state['custom_sequences'].get(i, str(row.get('SEQUENCE', '---')))
        id_p = int(row['ORDEM_PARADA'])
        
        if busca and (busca not in rua.upper() and busca not in bairro.upper() and busca not in seq_v.upper()): continue
        
        entregue = i in entregues_list
        is_next = (restantes_indices and i == restantes_indices[0])
        c_style = "next-target" if is_next else ""

        with st.container():
            st.markdown(f'<div class="delivery-card {c_style}">', unsafe_allow_html=True)
            if entregue:
                st.markdown(f'<span class="address-header" style="color: #dc3545;">:red[{id_p}ª - {rua} (FEITO)]</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="address-header">{id_p}ª - {rua}</div>', unsafe_allow_html=True)
            st.write(f"**Bairro:** {bairro}")
            
            c1, c2, c3 = st.columns([0.8, 2, 1.5])
            with c1:
                if st.checkbox("OK", key=f"c_{i}_{st.session_state['versao_lista']}", value=entregue):
                    if i not in st.session_state['entregues']:
                        st.session_state['entregues'].add(i); st.rerun()
                elif entregue:
                    st.session_state['entregues'].remove(i); st.rerun()
            with c2:
                st.session_state['custom_sequences'][i] = st.text_input("SEQUENCE:", value=seq_v, key=f"s_{i}_{st.session_state['versao_lista']}", label_visibility="collapsed")
            with c3:
                st.link_button("🚀 WAZE", f"https://waze.com/ul?ll={row['LATITUDE']},{row['LONGITUDE']}&navigate=yes", use_container_width=True, disabled=entregue)
            st.markdown('</div>', unsafe_allow_html=True)