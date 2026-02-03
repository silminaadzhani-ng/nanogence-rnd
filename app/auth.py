from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models import User
import streamlit as st

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, email, password):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def check_authentication():
    """
    To be called at the top of every page.
    If not authenticated, stops execution and shows warning.
    """
    if "user_email" not in st.session_state or not st.session_state.user_email:
        st.warning("⚠️ Access Denied. Please Login on the Dashboard.")
        st.stop()
    return True
