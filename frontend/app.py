"""ChargePin application entry point."""
import streamlit as st

from user_app import launch

st.set_page_config(page_title="ChargePin", page_icon="⚡", layout="wide", initial_sidebar_state="auto")
launch()
