st.markdown("""
    <style>
    /* 1. RESET E TRAVAS GLOBAIS */
    * { box-sizing: border-box !important; }
    html, body, [data-testid="stAppViewContainer"] { 
        overflow-x: hidden !important; width: 100% !important; 
    }
    .block-container { padding: 0.5rem 0.3rem !important; }
    header, footer, #MainMenu { visibility: hidden; }

    /* 2. GRID DA LISTA (O CORAÇÃO DO LAYOUT) */
    [data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: 52px 52px 1fr !important; /* Larguras iguais e compactas */
        gap: 4px !important;
        width: 100% !important;
        align-items: center !important;
    }
    
    [data-testid="column"] { width: 100% !important; min-width: 0 !important; }

    /* 3. CENTRALIZAÇÃO ABSOLUTA DOS ÍCONES (✅ e 🚗) */
    /* Removemos o padding e centralizamos o conteúdo dos botões */
    .stButton > button, .stLinkButton > a {
        height: 42px !important; /* Altura confortável para o dedo */
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 8px !important;
        border: 1px solid #dee2e6 !important;
        overflow: hidden !important;
    }

    /* Ajuste específico para o emoji dentro do botão */
    .stButton > button div p, .stLinkButton > a div {
        font-size: 18px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* 4. INPUT DA ORDEM (SEQUENCE) */
    .stTextInput input {
        height: 42px !important;
        background-color: #f8f9fa !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        text-align: center !important;
        border-radius: 8px !important;
        padding: 0 !important;
    }

    /* 5. CARDS E MÉTRICAS */
    .delivery-card { 
        border-radius: 8px; padding: 8px; background-color: white; 
        border-left: 5px solid #FF4B4B; margin: 4px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .next-target { border-left: 5px solid #007BFF !important; background-color: #f0f8ff !important; }
    .address-header { font-size: 12px !important; font-weight: 700; line-height: 1.2; }

    .custom-metrics-container {
        display: flex; justify-content: space-between; padding: 8px;
        background: white; border-radius: 8px; margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)