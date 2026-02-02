import streamlit as st
import os

def display_logo():
    # Final cleanup: Removed all corporate font overrides and logo images.
    st.markdown(
        """
        <style>
        /* Revert to default Streamlit behavior */
        .stButton > button {
            border-radius: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    # Sidebar logo/branding section entirely removed as requested.
    pass
