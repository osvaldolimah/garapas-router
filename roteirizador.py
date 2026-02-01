import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from folium.features import DivIcon
import requests
import pickle
import os

# --- 1. PERSISTÊNCIA DE DADOS ---
SAVE_FILE = "sessao_garapas.pkl"

def salvar_progresso():
    dados = {
        'df_final': st.session_state.get('df_final'),
        'road_path': st.session_state.get('road_path'),
        'entregues': st.session_state.get('entregues'),
        'manual_sequences': st.session_state.get('manual_sequences')
    }
    with open(SAVE_FILE, 'wb') as f:
        pickle.dump(dados, f)

def carregar_progresso():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'rb') as f:
                dados = pickle.load(f)
                for k, v in dados.items():
                    st.session_state[k] = v
                return True
        except: return False
    return False

# --- 2. FUNÇÕES TÉCNICAS (OTIMIZADAS COM CACHE) ---
def fast_haversine(lat1, lon1, lat2, lon2):
    p = np.pi/180
    a = 0.5 - np.cos((lat2-lat1)*p)/2 + np.cos(lat1*p) * np.cos(lat2*p) * (1-np.cos((lon2-lon1)*p))/2
    return 12742 * np.arcsin(np.sqrt(a))

@st.cache_data(show_spinner=False)
def get_road_route_batch(points_tuple):
    """Gera a rota seguindo as ruas através de requisições segmentadas mais robustas"""
    points = list(points_tuple)
    if len(points) < 2: return points
    
    full_path = []
    # Processamos em pedaços pequenos para garantir que a API siga as ruas com precisão
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i+1]
        
        url = f"https://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                coords = r.json()['routes'][0]['geometry']['coordinates']
                path_segment = [[c[1], c[0]] for c in coords]
                if full_path:
                    full_path.extend(path_segment[1:]) # Evita duplicar o ponto de conexão
                else:
                    full_path.extend(path_segment)
            else:
                full_path.extend([list(p1), list(p2)])
        except:
            full_path.extend([list(p1), list(p2)])
            
    return full_path if full_path else points

# --- 3. DESIGN SYSTEM: USANDO GRID COM PIXELS FIXOS ---
st.set_page_config(page_title="Garapas Router", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    /* 1. RESET TOTAL */
    * {
        box-sizing: border-box !important;
        margin: 0 !important;
    }
   
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stApp"], .main, .block-container {
        overflow-x: hidden !important;
        width: 100% !important;
        max-width: 100vw !important;
        padding: 0 !important;
    }
   
    .block-container {
        padding: 0.5rem 0.3rem !important;
    }
   
    header, footer, #MainMenu { visibility: hidden; }
    .leaflet-control-attribution { display: none !important; }

    /* 2. MÉTRICAS */
    .custom-metrics-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: white;
        padding: 8px 10px;
        border-radius: 8px;
        margin: 8px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 100%;
    }

    /* 3. GRID COM PIXELS FIXOS - A ÚNICA SOLUÇÃO GARANTIDA */
    [data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: 55px 55px 1fr !important;
        gap: 4px !important;
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
   
    [data-testid="column"] {
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
   
    [data-testid="column"]:nth-of-type(1) {
        width: 55px !important;
        max-width: 55px !important;
    }
   
    [data-testid="column"]:nth-of-type(2) {
        width: 55px !important;
        max-width: 55px !important;
    }
   
    [data-testid="column"]:nth-of-type(3) {
        width: 100% !important;
        min-width: 0 !important;
    }

    /* 4. CARDS */
    .delivery-card {
        border-radius: 8px;
        padding: 8px 10px;
        background-color: white;
        border-left: 4px solid #FF4B4B;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .next-target {
        border-left: 4px solid #007BFF !important;
        background-color: #f0f8ff !important;
        box-shadow: 0 2px 6px rgba(0,123,255,0.15) !important;
    }
    .address-header {
        font-size: 13px !important;
        font-weight: 700;
        color: #111;
        line-height: 1.3;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
   
    /* 5. BOTÕES E INPUTS */
    .stTextInput input {
        height: 40px !important;
        background-color: #f8f9fa !important;
        color: #000 !important;
        font-size: 14px !important;
        text-align: center;
        font-weight: 700 !important;
        border-radius: 6px !important;
        padding: 0 4px !important;
        border: 1px solid #dee2e6 !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
   
    .stButton button {
        height: 40px !important;
        font-size: 17px !important;
        width: 100% !important;
        border-radius: 6px !important;
        padding: 6px !important;
        box-sizing: border-box !important;
        white-space: nowrap !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }
   
    .stLinkButton a {
        height: 40px !important;
        font-size: 17px !important;
        width: 100% !important;
        border-radius: 6px !important;
        padding: 6px !important;
        box-sizing: border-box !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-decoration: none !important;
        transition: background-color 160ms ease, transform 120ms ease;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    /* 6. MOBILE - BOTÕES AINDA MENORES */
    @media screen and (max-width: 480px) {
        [data-testid="stHorizontalBlock"] {
            grid-template-columns: 50px 50px 1fr !important;
            gap: 3px !important;
        }
       
        [data-testid="column"]:nth-of-type(1) {
            width: 50px !important;
            max-width: 50px !important;
        }
       
        [data-testid="column"]:nth-of-type(2) {
            width: 50px !important;
            max-width: 50px !important;
        }
       
        .stButton button {
            font-size: 16px !important;
            height: 38px !important;
        }
        .stLinkButton a {
            font-size: 16px !important;
            height: 38px !important;
        }
        .stTextInput input {
            font-size: 13px !important;
            height: 38px !important;
        }
    }
   
    @media screen and (max-width: 360px) {
        [data-testid="stHorizontalBlock"] {
            grid-template-columns: 45px 45px 1fr !important;
            gap: 2px !important;
        }
       
        [data-testid="column"]:nth-of-type(1) {
            width: 45px !important;
            max-width: 45px !important;
        }
       
        [data-testid="column"]:nth-of-type(2) {
            width: 45px !important;
            max-width: 45px !important;
        }
       
        .stButton button {
            font-size: 15px !important;
            height: 36px !important;
        }
        .stLinkButton a {
            font-size: 15px !important;
            height: 36px !important;
        }
        .stTextInput input {
            font-size: 12px !important;
            height: 36px !important;
        }
    }

    /* 7. TABLETS */
    @media screen and (min-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            grid-template-columns: 60px 60px 1fr !important;
        }
       
        [data-testid="column"]:nth-of-type(1),
        [data-testid="column"]:nth-of-type(2) {
            width: 60px !important;
            max-width: 60px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. ESTADO ---
if 'df_final' not in st.session_state:
    if not carregar_progresso():
        st.session_state.update({
            'df_final': None,
            'road_path': [],
            'entregues': set(),
            'manual_sequences': {},
            'first_render': True
        })

# --- 5. MOTOR DE OPERAÇÃO (SUAVIZAÇÃO DA ATUALIZAÇÃO) ---
@st.fragment
def render_operacao():
    df_res = st.session_state['df_final']
    entregues_set = st.session_state['entregues']
    restantes = [i for i in range(len(df_res)) if i not in entregues_set]
   
    # --- A. MAPA (PREPARAÇÃO) ---
    all_coords = [[row['LATITUDE'], row['LONGITUDE']] for _, row in df_res.iterrows()]
   
    # Cálculo do centro para evitar o "bug do mapa do mundo"
    if all_coords:
        center_lat = sum(c[0] for c in all_coords) / len(all_coords)
        center_lon = sum(c[1] for c in all_coords) / len(all_coords)
    else:
        center_lat, center_lon = 0, 0

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="cartodbpositron",
        attribution_control=False
    )

    if st.session_state['road_path']:
        # Amostragem reduzida (::2) para seguir as curvas das ruas com precisão
        folium.PolyLine(st.session_state['road_path'][::2], color="#007BFF", weight=1, opacity=0.7).add_to(m)
   
    proximo_idx = restantes[0] if restantes else None
   
    for i, row in df_res.iterrows():
        foi = i in entregues_set
        cor = "#2ecc71" if foi else ("#007BFF" if (i == proximo_idx) else "#e74c3c")
        loc = [row['LATITUDE'], row['LONGITUDE']]
       
        # HTML Simplificado para renderização instantânea
        icon_html = f'<div style="background:{cor};border:1px solid white;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:8px;">{int(row["ORDEM_PARADA"])}</div>'
        folium.Marker(location=loc, icon=DivIcon(icon_size=(18,18), icon_anchor=(9,9), html=icon_html)).add_to(m)
   
    # ESTABILIZADOR: fit_bounds apenas quando necessário (evita piscada agressiva de Tiles)
    if all_coords and st.session_state.get('first_render', True):
        m.fit_bounds(all_coords, padding=(30, 30))
        st.session_state['first_render'] = False
   
    # Uso de chave estática e sem retorno de objetos para performance total
    st_folium(m, width=None, height=320, use_container_width=True, key="mapa_operacional", returned_objects=[])

    # --- B. MÉTRICAS ---
    km_v = sum(fast_haversine(df_res.iloc[restantes[k]]['LATITUDE'], df_res.iloc[restantes[k]]['LONGITUDE'],
                              df_res.iloc[restantes[k+1]]['LATITUDE'], df_res.iloc[restantes[k+1]]['LONGITUDE'])
              for k in range(len(restantes)-1)) if len(restantes) > 1 else 0
   
    st.markdown(f'<div class="custom-metrics-container"><div style="text-align:center; flex:1;"><span style="font-size:8px; color:#888; font-weight:bold; text-transform:uppercase;">📦 Restam</span><span style="font-size:14px; color:#111; font-weight:800; display:block;">{len(restantes)}</span></div><div style="text-align:center; flex:1;"><span style="font-size:8px; color:#888; font-weight:bold; text-transform:uppercase;">🛤️ KM</span><span style="font-size:14px; color:#111; font-weight:800; display:block;">{km_v * 1.3:.1f} km</span></div></div>', unsafe_allow_html=True)
   
    # --- C. LISTA DE ENTREGAS ---
    with st.container(height=500):
        for i, row in df_res.iterrows():
            rua, uid = str(row.get('DESTINATION ADDRESS', '---')), str(row.get('UID', ''))
            val_padrao = st.session_state['manual_sequences'].get(uid, str(row.get('SEQUENCE', '---')))
            entregue, is_next = i in entregues_set, (i == proximo_idx)
            card_class = "next-target" if is_next else ""

            st.markdown(f'<div class="delivery-card {card_class}"><div class="address-header">{int(row["ORDEM_PARADA"])}ª - {rua}</div></div>', unsafe_allow_html=True)
           
            c_done, c_waze, c_seq = st.columns(3)
            with c_done:
                if st.button("✅" if not entregue else "🔄", key=f"d_{i}", use_container_width=True):
                    if entregue: st.session_state['entregues'].remove(i)
                    else: st.session_state['entregues'].add(i)
                    salvar_progresso()
                    st.rerun(scope="fragment") # Atualização suave do bloco
            with c_waze:
                st.link_button("🚗", f"https://waze.com/ul?ll={row['LATITUDE']},{row['LONGITUDE']}&navigate=yes", use_container_width=True)
            with c_seq:
                nova_seq = st.text_input("", value=val_padrao, key=f"s_{i}", label_visibility="collapsed")
                if nova_seq != val_padrao:
                    st.session_state['manual_sequences'][uid] = nova_seq
                    salvar_progresso()

# --- 6. INTERFACE PRINCIPAL ---
if st.session_state['df_final'] is None:
    st.subheader("🚚 Garapas Router")
    uploaded_file = st.file_uploader("Subir Manifestos", type=['xlsx'])
    if uploaded_file and st.button("🚀 Iniciar Rota", use_container_width=True):
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        df_clean = df_raw.dropna(subset=['LATITUDE', 'LONGITUDE'])
        df_clean['UID'] = df_clean['DESTINATION ADDRESS'].astype(str) + df_clean['SEQUENCE'].astype(str)
        df_temp = df_clean.copy().reset_index()
        rota = []
        p_atual = df_temp.iloc[0]; rota.append(p_atual); df_temp = df_temp.drop(df_temp.index[0])
        while not df_temp.empty:
            dists = fast_haversine(p_atual['LATITUDE'], p_atual['LONGITUDE'], df_temp['LATITUDE'].values, df_temp['LONGITUDE'].values)
            idx = np.argmin(dists); p_atual = df_temp.iloc[idx]; rota.append(p_atual); df_temp = df_temp.drop(df_temp.index[idx])
        final_df = pd.DataFrame(rota).reset_index(drop=True)
        final_df['ORDEM_PARADA'] = range(1, len(final_df) + 1)
        st.session_state['df_final'] = final_df
        st.session_state['first_render'] = True
        pts_tuple = tuple(map(tuple, final_df[['LATITUDE', 'LONGITUDE']].values.tolist()))
        st.session_state['road_path'] = get_road_route_batch(pts_tuple)
        salvar_progresso()
        st.rerun()

else:
    # BOTÕES DE CONTROLE
    c_limpar, c_novo = st.columns(2)
    with c_limpar:
        if st.button("🗑️", use_container_width=True):
            restantes_idxs = [i for i in range(len(st.session_state['df_final'])) if i not in st.session_state['entregues']]
            if restantes_idxs:
                st.session_state['df_final'] = st.session_state['df_final'].iloc[restantes_idxs].reset_index(drop=True)
                st.session_state['df_final']['ORDEM_PARADA'] = range(1, len(st.session_state['df_final']) + 1)
                st.session_state['entregues'] = set()
                st.session_state['first_render'] = True
                pts_tuple = tuple(map(tuple, st.session_state['df_final'][['LATITUDE', 'LONGITUDE']].values.tolist()))
                st.session_state['road_path'] = get_road_route_batch(pts_tuple)
                salvar_progresso()
                st.rerun()
    with c_novo:
        if st.button("📁", use_container_width=True):
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            st.session_state.clear()
            st.rerun()

    # Chamar o motor de operação (Mapa + Métricas + Lista)
    render_operacao()