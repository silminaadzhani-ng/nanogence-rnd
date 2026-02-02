import streamlit as st
import os

def display_logo():
    # 1. Inject Theme & Font (Helvetica) - Global CSS
    st.markdown(
        """
        <style>
        /* Force Helvetica Font globally */
        @import url('https://fonts.cdnfonts.com/css/helvetica-neue-9');
        
        * {
            font-family: 'Helvetica', 'Arial', sans-serif !important;
        }

        /* Streamlit Specific Font Locking */
        .main .block-container, .stMarkdown, .stText, .stButton, .stSelectbox, .stTextInput, .stNumberInput {
            font-family: 'Helvetica', 'Arial', sans-serif !important;
        }

        /* Branding Colors (Nanogence Blue) */
        :root {
            --nanogence-blue: #2F76B5;
        }

        /* Primary Action Styling */
        div[data-testid="stMetricValue"] {
            color: var(--nanogence-blue);
        }
        
        .stButton > button {
            border: 1px solid var(--nanogence-blue);
            color: var(--nanogence-blue);
        }
        
        .stButton > button:hover {
            background-color: var(--nanogence-blue);
            color: white;
        }
        
        /* Sidebar Logo Header */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding-top: 0rem !important;
        }

        /* Top Left Corner Logo Placement Styling */
        .sidebar-logo-container {
            margin-top: -3rem;
            margin-left: -1rem;
            margin-right: -1rem;
            background-color: var(--nanogence-blue);
            padding: 10px;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 2. Display Logo at the absolute top of the sidebar
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(logo_path):
        # We place the image directly. Streamlit sidebar items go from top down.
        st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
