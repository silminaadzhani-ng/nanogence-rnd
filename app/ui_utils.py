import streamlit as st
import os

def display_logo():
    # Display Official Logo
    if os.path.exists("assets/nanogence_logo.jpg"):
        st.sidebar.image("assets/nanogence_logo.jpg", use_container_width=True)

    # Apply Corporate Theme
    st.markdown(
        """
        <style>
        /* Primary Accent Color - Nanogence Blue */
        :root {
            --primary-color: #2E6DA4;
        }
        
        /* Button Styling */
        .stButton > button {
            border-radius: 6px;
            font-weight: 500;
        }
        
        /* Sidebar styling to match logo background subtly */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }
        
        /* Headings */
        h1, h2, h3 {
            color: #2E6DA4;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
