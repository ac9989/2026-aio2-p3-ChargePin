"""ChargePin 1.0 Streamlit interface connected to the preview multi-agent backend."""
from __future__ import annotations

from pathlib import Path
from html import escape
import json
from math import asin, cos, radians, sin, sqrt
import os
import re
from typing import Any

import streamlit as st

from api_client import ApiError, ChargePinApi
from capture_notice import install_capture_notice
from dashboard_data import can_view_dashboard
from dashboard_view import MENUS as DASHBOARD_MENUS, render_operations_dashboard
from map_view import build_map_html
from redesign_theme import REDESIGN_STYLES


st.set_page_config(page_title="ChargePin", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

def record_api_event(event: dict[str, Any]) -> None:
    events = list(st.session_state.get("api_events", []))
    events.append(event)
    st.session_state.api_events = events[-100:]


API = ChargePinApi(observer=record_api_event)
CONNECTOR_CODES = {"급속": "FAST", "완속": "SLOW"}
ROLE_LABELS = {"GUEST": "일반 이용자", "JUNIOR_ADMIN": "하급 관리자", "SENIOR_ADMIN": "상급 관리자"}

STYLES = """
<style>
@font-face { font-family:"Pretendard Variable"; src:url("/app/static/fonts/PretendardVariable.woff2") format("woff2"); font-weight:45 920; font-display:swap; }
.stApp, .stApp :is(button, input, textarea, select, p, label, h1, h2, h3, h4, [data-testid="stMarkdownContainer"]) { font-family:"Pretendard Variable", "Malgun Gothic", sans-serif; }
[data-testid="stAppViewContainer"] { background:#FFFFFF !important; }
[data-testid="stMainBlockContainer"] { max-width:1440px; padding-top:1.7rem; }
.brand-row { min-height:52px; margin:0 !important; }
.brand-bolt { width:46px !important; height:46px !important; border-radius:15px !important; background:#292E35 !important; color:#FFB42F !important; font-family:Arial,sans-serif !important; font-size:25px !important; }
.brand-name { color:#20262D !important; font-size:22px !important; }
.brand-sub { color:#536170 !important; font-size:12px !important; }
.header-actions { display:flex; }
:is(.st-key-header_settings,.st-key-header_power) button { width:46px !important; height:46px !important; min-height:46px !important; border-radius:50% !important; padding:0 !important; border:1px solid #CBD3DA !important; background:#F5F7F9 !important; color:#29343E !important; }
:is(.st-key-header_settings,.st-key-header_power) button p { font-size:0 !important; line-height:0 !important; }
:is(.st-key-header_settings,.st-key-header_power) button [data-testid="stIconMaterial"] { font-size:23px !important; }
:is(.st-key-header_settings,.st-key-header_power) button [data-has-shortcut] { gap:0 !important; }
.st-key-user_brand { gap:10px !important; min-height:52px; }
.st-key-status_bolt button[data-testid="stPopoverButton"] { display:grid; place-items:center; width:46px !important; height:46px !important; min-height:46px !important; padding:0 !important; border:0 !important; border-radius:15px !important; background:#292E35 !important; color:#FFB42F !important; }
.st-key-status_bolt button[data-testid="stPopoverButton"]:hover { background:#40464D !important; }
.st-key-status_bolt button[data-testid="stPopoverButton"] p { font-size:0 !important; line-height:0 !important; }
 .st-key-status_bolt button[data-testid="stPopoverButton"] { position:relative; }
.st-key-status_bolt button[data-testid="stPopoverButton"] [data-testid="stIconMaterial"] { visibility:hidden; font-size:28px !important; }
.st-key-status_bolt button[data-testid="stPopoverButton"]::before, .brand-bolt::before {
  content:""; display:block; width:29px; height:29px; position:absolute;
  background:linear-gradient(155deg,#FFD064 5%,#FF8E3C 52%,#EC4F51 100%);
  mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M13.6 2.2 5.4 13h5.5L9.8 21.8 18.6 10h-5.4l.4-7.8Z'/%3E%3C/svg%3E") center/contain no-repeat;
}
.brand-bolt { position:relative; font-size:0 !important; }
.st-key-status_bolt button[data-testid="stPopoverButton"] div[aria-hidden="true"] { display:none; }
.st-key-status_bolt button[data-testid="stPopoverButton"] [data-has-shortcut] { gap:0 !important; }
[data-testid="stMain"]:has(.dashboard-marker) .brand-name { color:#FFFFFF !important; }
[data-testid="stMain"]:has(.dashboard-marker) .brand-sub { color:#CED4DA !important; }
[data-testid="stMain"]:has(.dashboard-marker) .st-key-status_bolt button[data-testid="stPopoverButton"] { background:#41474F !important; }
[data-testid="stMain"]:has(.dashboard-marker) :is(.st-key-header_settings,.st-key-header_power) button { background:#41474F !important; border-color:#6A717A !important; color:#FFFFFF !important; }
[data-testid="stMain"]:has(.dashboard-marker) hr { border-color:#555B63 !important; }
[data-testid="stMain"]:has(.dashboard-marker) [data-testid="stMetricLabel"] p { font-size:.88rem !important; font-weight:650 !important; color:#536170 !important; }
[data-testid="stMain"]:has(.dashboard-marker) [data-testid="stMetricValue"] { font-size:1.55rem !important; line-height:1.25 !important; font-weight:750 !important; }
.st-key-mode [data-testid="stRadioGroup"] { display:flex; width:100%; gap:8px; }
.st-key-mode [data-testid="stRadioOption"] { display:flex; flex:1; justify-content:center; border:1px solid #CED4DA; border-radius:10px; background:#FFFFFF; padding:9px 12px; cursor:pointer; }
.st-key-mode [data-testid="stRadioOption"] > div > div:first-child { display:none; }
.st-key-mode [data-testid="stRadioOption"][data-selected="true"] { background:#30343A; border-color:#30343A; }
.st-key-mode [data-testid="stRadioOption"] p { color:#30343A !important; font-weight:700; }
.st-key-mode [data-testid="stRadioOption"][data-selected="true"] p { color:#FFFFFF !important; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] { background:#30343A !important; color:#FFFFFF !important; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] span { color:#FFFFFF !important; }
.st-key-search_panel { padding:22px !important; border:1px solid #DDE2E7 !important; border-radius:20px !important; background:#FFFFFF; box-shadow:0 8px 24px #1F2A350A; gap:12px !important; }
.st-key-search_panel:has([data-testid="stChatInput"]) { min-height:575px; }
.st-key-search_panel .search-title { margin:0 0 14px; font-size:25px; line-height:1.35; }
.st-key-search_panel [data-testid="stWidgetLabel"] { margin-bottom:4px; }
.st-key-search_panel [data-testid="stWidgetLabel"] p { color:#303A44; font-size:14px; font-weight:650; }
.st-key-search_panel .st-key-mode [data-testid="stRadioGroup"] { margin-bottom:4px; }
.st-key-search_panel div.stButton button[kind="primary"] { min-height:46px; }
@media(max-width:768px) { .st-key-search_panel { padding:18px !important; } }
.st-key-search_header { position:sticky; top:0; z-index:100; background:#FFFFFF; }
.st-key-dashboard_header { position:sticky; top:0; z-index:100; isolation:isolate; padding-bottom:0 !important; margin-bottom:18px; }
.st-key-dashboard_header::before { content:""; position:absolute; z-index:-1; left:50%; width:100vw; top:-100px; bottom:0; transform:translateX(-50%); background:#292E35; pointer-events:none; }
.st-key-dashboard_navigation [data-testid="stRadioGroup"] { gap:20px; flex-wrap:wrap; }
.st-key-dashboard_navigation [data-testid="stRadioOption"] { border:0; border-bottom:3px solid transparent; border-radius:0; padding:12px 0 10px; background:transparent; cursor:pointer; }
.st-key-dashboard_navigation [data-testid="stRadioOption"] > div > div:first-child { display:none; }
.st-key-dashboard_navigation [data-testid="stRadioOption"] p { color:#CFD5DC !important; font-weight:650; }
.st-key-dashboard_navigation [data-testid="stRadioOption"][data-selected="true"] { border-bottom-color:#FFBC42; }
.st-key-dashboard_navigation [data-testid="stRadioOption"][data-selected="true"] p { color:#FFFFFF !important; }
[data-testid="stMain"] { color:#202830; }
[data-testid="stMain"] :is(h1,h2,h3,h4,[data-testid="stMetricValue"],[data-testid="stMetricLabel"],[data-testid="stTabs"] [role="tab"]) { color:#202830 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:#536170 !important; }
[data-testid="stAlert"] p { color:#253746 !important; }
:root { --cp-ink:#26313C; --cp-muted:#71808D; --cp-line:#D8E1E8; --cp-soft:#F5F8FA; --cp-surface:#FFF; --cp-gold:#F5CB46; --cp-gold-deep:#A27A18; --cp-alert:#B85D4A; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display:none !important; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stAppViewContainer"] { background:linear-gradient(135deg,#FBFCFD 0%,#FFFDF7 100%); }
[data-testid="stMainBlockContainer"] { max-width:1440px; padding-top:1.7rem; }
.brand-row { display:flex; align-items:center; gap:10px; margin:0 0 4px; }
.brand-bolt { display:grid; place-items:center; width:32px; height:32px; border-radius:11px; background:var(--cp-gold); color:#333; font-size:17px; }
.brand-name { color:var(--cp-ink); font-size:21px; font-weight:850; letter-spacing:-.05em; }
.brand-sub { color:var(--cp-muted); font-size:12px; margin-top:2px; }
.shell-card { background:var(--cp-surface); border:1px solid var(--cp-line); border-radius:19px; padding:20px; box-shadow:0 10px 30px #2030400d; }
.search-kicker { color:var(--cp-gold-deep); font-size:11px; font-weight:850; letter-spacing:.12em; }
.search-title { color:var(--cp-ink); font-size:21px; font-weight:850; letter-spacing:-.045em; margin:6px 0 3px; }
.search-copy { color:var(--cp-muted); font-size:12px; line-height:1.55; margin-bottom:15px; }
.summary { padding:10px 12px; border-radius:11px; background:#FFF9E9; border:1px solid #F0E2B7; color:#5C4B26; font-size:12px; font-weight:700; line-height:1.5; margin:9px 0; }
.map-shell { position:relative; height:525px; overflow:hidden; border:1px solid #DCE8E5; border-radius:21px; background:#F2F7F2; box-shadow:0 10px 28px #536d6712; }
.map-grid { position:absolute; inset:0; background:linear-gradient(112deg,transparent 37%,#DCEEF2 37%,#DCEEF2 47%,transparent 47%),linear-gradient(0deg,transparent 39%,#FFF 39%,#FFF 40%,transparent 40%),linear-gradient(90deg,transparent 61%,#FFF 61%,#FFF 62%,transparent 62%),#F3F7F3; }
.map-label { position:absolute; top:14px; left:14px; z-index:5; max-width:78%; padding:8px 11px; border-radius:9px; background:#FFF; box-shadow:0 2px 10px #1232; color:#51412B; font-size:12px; }
.radius-ring { position:absolute; width:45%; aspect-ratio:1; left:27.5%; top:28%; border:2px dashed #C3922E; background:#F6D66F24; border-radius:50%; }
.center-dot { position:absolute; left:50%; top:50%; width:14px; height:14px; transform:translate(-50%,-50%); border:2px solid #FFF; border-radius:5px; background:#3A2D1B; }
.map-marker { position:absolute; z-index:3; transform:translate(-50%,-50%); }
.map-marker:hover, .map-marker:focus-within { z-index:10; }
.map-pin { width:37px; height:37px; border:2px solid #FFF; border-radius:50%; background:#40331D; box-shadow:0 2px 6px #0003; color:#FFF; cursor:pointer; font-weight:800; }
.map-pop { visibility:hidden; opacity:0; position:absolute; left:50%; bottom:calc(100% + 9px); width:240px; transform:translateX(-50%); padding:13px; border:1px solid #DEE5EA; border-radius:13px; background:#FFF; box-shadow:0 10px 28px #2433422B; color:var(--cp-ink); transition:.14s; }
.map-marker:hover .map-pop, .map-marker:focus-within .map-pop, .map-marker.open .map-pop { visibility:visible; opacity:1; }
.map-pop-title { font-size:13px; font-weight:800; margin-bottom:8px; }.map-pop-row { display:flex; justify-content:space-between; gap:8px; padding:3px 0; font-size:11px; }.map-pop-row span{color:#778490}.map-pop-row b{text-align:right}.map-pop-note{margin-top:7px;padding-top:7px;border-top:1px solid #EDF0F2;color:#8A959F;font-size:10px;line-height:1.4}
.map-legend { position:absolute; left:14px; bottom:14px; z-index:5; padding:9px 11px; border-radius:9px; background:#FFF; color:#5A472D; font-size:12px; box-shadow:0 2px 10px #1232; }
.station-card { border:1px solid #E5EAF0; border-radius:14px; padding:14px; background:#FFF; margin:9px 0; }.station-name{color:var(--cp-ink);font-size:14px;font-weight:800}.station-address{color:var(--cp-muted);font-size:11px;margin:4px 0 9px}.station-meta{display:flex;gap:7px;flex-wrap:wrap}.chip{display:inline-block;border-radius:999px;padding:4px 8px;background:#F4F7F9;color:#4A5968;font-size:10px;font-weight:750}.chip.ok{background:#E9F3E7;color:#386443}.chip.warn{background:#FFF3D6;color:#8A5E12}.status-line{margin-top:9px;color:#34424E;font-size:12px;font-weight:750}
.station-detail { display:flex; justify-content:space-between; gap:10px; margin-top:6px; color:#536170; font-size:12px; line-height:1.4; } .station-detail span:last-child { color:#202830; text-align:right; overflow-wrap:anywhere; }
.dashboard-hero { padding:19px; margin:12px 0 16px; border-radius:17px; background:#FFF9E9; border:1px solid #F0E2B7; }.metric-label{color:var(--cp-muted);font-size:11px;font-weight:750}.metric-value{color:var(--cp-ink);font-size:24px;font-weight:850;letter-spacing:-.05em}.detail-row{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #EEF1F3;font-size:14px;color:#26313C}.detail-row:last-child{border-bottom:0}
.st-key-login-form { border:1px solid #AEB8C2 !important; border-radius:14px !important; padding:24px !important; }
.st-key-login-form [data-testid="stVerticalBlock"] { gap:16px !important; }
.st-key-login-form h3 { margin:0 !important; padding:0 0 4px !important; font-size:25px !important; line-height:1.35 !important; }
.st-key-login-form [data-testid="stTextInput"] [data-baseweb="input"] { border:1px solid #CCD3DA !important; border-radius:10px; }
.st-key-login-form [data-testid="stFormSubmitButton"] button { min-height:46px; }
[data-testid="stFormSubmitButton"] button { background:#30343A !important; border:1px solid #30343A !important; color:#FFFFFF !important; }
[data-testid="stFormSubmitButton"] button p { color:#FFFFFF !important; }
[data-testid="stFormSubmitButton"] button:hover { background:#454A51 !important; border-color:#454A51 !important; }
div.stButton > button { border-radius:11px; font-weight:750; } div.stButton > button[kind="primary"] { background:#30343A; border-color:#30343A; color:#FFFFFF; }
div.stButton > button[kind="primary"] p { color:#FFFFFF !important; }
div.stButton > button[kind="primary"]:hover { background:#454A51; border-color:#454A51; color:#FFFFFF; }

.station-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; max-height:580px; overflow-y:scroll; scrollbar-gutter:stable; scrollbar-width:auto; scrollbar-color:#9BAAB6 #EDF1F4; padding:2px 8px 4px 2px; }
.station-grid::-webkit-scrollbar { width:12px; }
.station-grid::-webkit-scrollbar-track { background:#EDF1F4; border-radius:8px; }
.station-grid::-webkit-scrollbar-thumb { background:#9BAAB6; border:3px solid #EDF1F4; border-radius:8px; }
.station-grid .station-card { margin:0; padding:20px; border-color:#D3DAE2; min-width:0; }
.station-grid .station-name { font-size:17px; line-height:1.45; }
.station-grid .station-address { font-size:13px; line-height:1.5; margin:6px 0 12px; }
.station-grid .chip { font-size:12px; }
.station-grid .station-detail { display:grid; grid-template-columns:100px minmax(0,1fr); gap:12px; margin-top:9px; font-size:13px; line-height:1.5; }
.station-grid .status-line { margin:12px 0; }
.st-key-results_pager { margin-top:18px; gap:14px !important; align-items:center !important; }
.st-key-results_pager [data-testid="stElementContainer"] { align-self:center !important; }
.st-key-results_pager [data-testid="stMarkdownContainer"] p { margin:0 !important; }
.st-key-results_pager button { min-height:36px; padding:5px 14px; font-size:13px; border-radius:9px; }
.result-page { min-width:100px; min-height:36px; display:flex; align-items:center; justify-content:center; text-align:center; color:#536170; font-size:14px; font-variant-numeric:tabular-nums; }
@media(max-width:700px) { .station-grid { grid-template-columns:1fr; } }

/* Dashboard content spacing is isolated from the shared header and search UI. */
.st-key-dashboard_body { gap:12px !important; }
.st-key-dashboard_body [data-testid="stVerticalBlock"] { gap:10px; }
.st-key-dashboard_body [data-testid="stHorizontalBlock"] { gap:14px; }
.st-key-dashboard_body [data-testid="stVerticalBlockBorderWrapper"] > div,
.st-key-dashboard_body [data-testid="stVerticalBlock"][data-border="true"] { border-radius:12px; }
.st-key-dashboard_body [data-testid="stVerticalBlockBorderWrapper"] { border-color:#D7DFE7; }
.st-key-dashboard_body [class*="st-key-dashboard_card_"] { padding:20px !important; gap:14px !important; height:auto !important; min-height:min-content; overflow:visible !important; }
.st-key-dashboard_body [class*="st-key-dashboard_card_"] [data-testid="stMarkdownContainer"],
.st-key-dashboard_body [class*="st-key-dashboard_card_"] [data-testid="stCaptionContainer"] { overflow:visible !important; height:auto !important; }
.st-key-dashboard_body [data-testid="stCaptionContainer"] { margin:2px 0 4px; }
.st-key-dashboard_body .dashboard-empty { margin:2px 0 0; }
@media(max-width:700px) { .st-key-dashboard_body [class*="st-key-dashboard_card_"] { padding:16px !important; } }
.st-key-dashboard_body h4 { font-size:17px !important; font-weight:750; line-height:1.5; padding:0 !important; margin:0 0 4px !important; }
.st-key-dashboard_body [data-testid="stCaptionContainer"] p { font-size:12px !important; line-height:1.5; margin:0; color:#687685 !important; }
.st-key-dashboard_body [data-testid="stMetricLabel"] p { font-size:13px !important; font-weight:650 !important; }
.st-key-dashboard_body [data-testid="stMetricValue"] { font-size:24px !important; line-height:1.2 !important; font-weight:750 !important; }
.st-key-dashboard_body [data-testid="stMetric"] { padding:4px 0; }
.st-key-dashboard_body .detail-row { padding:8px 0; font-size:13px; align-items:center; gap:14px; }
.st-key-dashboard_body .detail-row b { font-size:12px; font-weight:650; text-align:right; color:#45576A; }
.dashboard-empty { display:flex; align-items:flex-start; gap:8px; padding:10px 12px; border-radius:8px; background:#F3F5F7; color:#637080; font-size:13px; line-height:1.5; }
.pending-dot { flex:0 0 6px; width:6px; height:6px; margin-top:7px; border-radius:50%; background:#96A2AF; }

/* All exploration filters share the same field surface and dimensions. */
.st-key-search_panel :is([data-testid="stSelectbox"],[data-testid="stMultiSelect"]) [data-baseweb="select"] > div {
    min-height:46px !important; background:#F3F5F7 !important;
    border:1px solid #D5DCE3 !important; border-radius:10px !important;
    box-shadow:none;
}
.st-key-search_panel [data-testid="stTextInput"] [data-baseweb="input"] {
    min-height:46px; background:#F3F5F7; border:1px solid #D5DCE3; border-radius:10px;
}
.st-key-search_panel :is([data-testid="stSelectbox"],[data-testid="stMultiSelect"],[data-testid="stTextInput"]) {
    margin-bottom:4px;
}
.st-key-search_panel [data-baseweb="select"] { font-size:14px; }
.st-key-search_panel [data-baseweb="tag"] { border-radius:6px; }

.st-key-chat_history { border:0 !important; padding:4px 2px 8px !important; scrollbar-width:thin; scrollbar-color:#BCC5CE transparent; }
.st-key-chat_history [data-testid="stChatMessage"] { padding:12px 8px; }
.st-key-chat_history [data-testid="stChatMessage"] p { font-size:15px; line-height:1.65; }
.st-key-search_panel [data-testid="stChatInput"] { margin-top:8px; }
@media(max-width:700px) { .st-key-chat_history { height:380px !important; } }

.instrument-cluster { padding:20px 22px 12px; background:linear-gradient(145deg,#303943,#20272F); border:1px solid #45505C; border-radius:20px; color:#F7F9FC; }
.cluster-heading { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:14px; font-weight:650; }
.cluster-source { color:#ACB8C6; font-size:12px; font-weight:400; }
.instrument-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; padding-top:20px; }
.instrument { min-width:0; text-align:center; }
.instrument-label { display:flex; align-items:center; justify-content:center; gap:7px; color:#D9E1EA; font-size:14px; font-weight:600; margin-bottom:10px; }
.instrument-led { width:6px; height:6px; border-radius:50%; background:#7C8794; }
.instrument-led.live { background:#6DE0B3; box-shadow:0 0 8px #6DE0B340; }
.instrument-led.fault { background:#FFBC68; }
.instrument svg { display:block; width:100%; max-width:230px; height:auto; margin:0 auto; font-family:"Pretendard Variable","Malgun Gothic",sans-serif; }
.st-key-dashboard_body [class*="st-key-dashboard_card_"] { border-radius:16px !important; }
.st-key-dashboard_body .dashboard-empty { background:#F1F4F6; }
@media(max-width:760px) { .instrument-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; } .instrument-cluster { padding:18px 16px 10px; } }

/* Light console panels: no decorative scales or fake telemetry. */
.st-key-dashboard_body { gap:20px !important; }
.st-key-dashboard_body > [data-testid="stElementContainer"]:has(.instrument-cluster) { margin-bottom:8px; }
.instrument-cluster { margin-bottom:8px; }
.st-key-dashboard_body [data-testid="stHorizontalBlock"] { gap:18px !important; }
.st-key-dashboard_body [data-testid="stColumn"] > [data-testid="stVerticalBlock"] { gap:18px !important; }
.st-key-dashboard_body [class*="st-key-dashboard_card_"] {
    padding:22px !important; gap:14px !important; border:1px solid #D9E0E6 !important;
    background:#FFFFFF; box-shadow:0 3px 12px #26313C04;
}
.st-key-dashboard_body :is(.st-key-dashboard_card_2,.st-key-dashboard_card_8,.st-key-dashboard_card_13) {
    background:linear-gradient(135deg,#F7F9FA,#EFF3F5);
}
.console-heading { display:flex; align-items:center; gap:9px; padding:0 0 4px; min-height:28px; }
.console-indicator { display:block; width:5px; height:16px; flex:0 0 5px; border-radius:3px; background:#718491; }
.st-key-dashboard_body .console-heading h4 { margin:0 !important; padding:0 !important; font-size:16px !important; line-height:1.5; }
.st-key-dashboard_body .detail-row { padding:9px 0; border-bottom-color:#EDF0F3; }
.st-key-dashboard_body .detail-row b { background:#F0F3F5; border-radius:6px; padding:4px 8px; font-size:12px; }
.st-key-dashboard_body .dashboard-empty { padding:12px 14px; margin:2px 0 0; background:#F0F3F5; border:1px solid #E7ECEF; color:#5C6B78; }
.st-key-dashboard_body :is(.st-key-dashboard_card_3,.st-key-dashboard_card_4) { min-height:240px; }
.st-key-dashboard_body :is(.st-key-dashboard_card_6,.st-key-dashboard_card_8) { min-height:220px; }
.st-key-dashboard_body :is(.st-key-dashboard_card_7,.st-key-dashboard_card_9) { min-height:158px; }
.st-key-dashboard_body :is(.st-key-dashboard_card_10,.st-key-dashboard_card_11) { min-height:140px; }
.deployment-stages { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; margin:6px 0 0; }
.deployment-stage { padding:14px 16px; background:#FFFFFF; border:1px solid #DCE3E9; border-radius:12px; }
.stage-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.stage-index { font-size:12px; font-weight:650; color:#7B8996; font-variant-numeric:tabular-nums; }
.stage-dot { width:6px; height:6px; border-radius:50%; background:#B7C2CB; }
.stage-title { font-size:15px; font-weight:700; color:#29343E; line-height:1.5; }
.stage-status { font-size:12px; color:#72808D; margin-top:4px; }
@media(max-width:760px) {
    .deployment-stages { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .st-key-dashboard_body [class*="st-key-dashboard_card_"] { padding:18px !important; min-height:0; }
}

/* Shared typography and alignment across user and operations views. */
.brand-name { font-size:26px !important; line-height:1.3 !important; font-weight:750; letter-spacing:-.035em; }
.brand-sub { font-size:14px !important; line-height:1.5; margin-top:5px; }
.brand-row { min-height:76px; gap:14px; }
.st-key-user_brand { min-height:76px; gap:14px !important; align-items:center; }
.brand-bolt,
.st-key-status_bolt button[data-testid="stPopoverButton"] {
    width:52px !important; height:52px !important; min-height:52px !important; border-radius:16px !important;
}
:is(.st-key-header_settings,.st-key-header_power) button {
    width:52px !important; height:52px !important; min-height:52px !important;
}
.st-key-dashboard_header { gap:20px !important; padding-bottom:4px !important; margin-bottom:24px; }
.st-key-dashboard_navigation [data-testid="stRadioGroup"] { gap:30px !important; }
.st-key-dashboard_navigation [data-testid="stRadioOption"] { padding:14px 4px 15px !important; }
.st-key-dashboard_navigation [data-testid="stRadioOption"] p { font-size:17px !important; line-height:1.5; }
.st-key-search_panel { padding:26px !important; gap:18px !important; }
.st-key-search_panel .search-title { font-size:28px; line-height:1.4; margin:0 0 18px; }
.st-key-search_panel [data-testid="stWidgetLabel"] p { font-size:16px !important; line-height:1.5; }
.st-key-search_panel [data-testid="stRadioOption"] p,
.st-key-search_panel [data-baseweb="select"],
.st-key-search_panel input { font-size:15px !important; }
.st-key-search_panel [data-testid="stRadioGroup"] { column-gap:22px; row-gap:12px; }
.st-key-search_panel .st-key-mode [data-testid="stRadioOption"] { padding:11px 18px; }
.st-key-search_panel [data-testid="stCaptionContainer"] p { font-size:13px !important; line-height:1.6; }
.st-key-dashboard_body { gap:22px !important; }
.st-key-dashboard_body [data-testid="stHorizontalBlock"] { gap:22px !important; }
.st-key-dashboard_body [class*="st-key-dashboard_card_"] { padding:24px !important; gap:16px !important; }
.st-key-dashboard_body .console-heading h4 { font-size:19px !important; line-height:1.5; }
.st-key-dashboard_body .detail-row { font-size:15px; padding:11px 0; }
.st-key-dashboard_body .detail-row b { font-size:13px; padding:5px 9px; }
.st-key-dashboard_body [data-testid="stCaptionContainer"] p { font-size:13px !important; line-height:1.6; }
.st-key-dashboard_body .dashboard-empty { font-size:14px; line-height:1.65; padding:13px 15px; }
.cluster-heading { font-size:16px; }
.cluster-source { font-size:13px; }
.instrument-label { font-size:15px; }
.stage-title { font-size:17px; }
.stage-status { font-size:14px; }
.stage-index { font-size:13px; }
.st-key-chat_history [data-testid="stChatMessage"] p { font-size:16px; line-height:1.7; }
@media(max-width:760px) {
    .brand-name { font-size:22px !important; }
    .brand-sub { font-size:13px !important; }
    .st-key-dashboard_navigation [data-testid="stRadioGroup"] { gap:18px !important; }
    .st-key-dashboard_navigation [data-testid="stRadioOption"] p { font-size:15px !important; }
    .st-key-search_panel { padding:20px !important; }
    .st-key-dashboard_body [class*="st-key-dashboard_card_"] { padding:20px !important; }
}

/* Single source of truth for shared header geometry. */
[data-testid="stMainBlockContainer"] { padding-top:10px !important; }
.st-key-common_header {
    box-sizing:border-box; height:88px !important; min-height:88px !important;
    padding:0 !important; margin:0 !important; align-items:center !important;
    flex-wrap:nowrap !important; gap:24px !important;
}
.st-key-common_header .st-key-user_brand {
    flex:1 1 0% !important; width:auto !important; min-width:0 !important;
    height:76px !important; min-height:76px !important; flex-wrap:nowrap !important;
    align-items:center !important; gap:14px !important;
}
.st-key-common_header .brand-name { white-space:nowrap; line-height:34px !important; margin:0; }
.st-key-common_header .brand-sub { white-space:nowrap; line-height:21px !important; margin-top:4px; }
.st-key-header_actions {
    box-sizing:border-box; flex:0 0 116px !important; width:116px !important;
    min-width:116px !important; max-width:116px !important; height:76px;
    gap:12px !important; flex-wrap:nowrap !important; align-items:center !important;
}
:is(.st-key-header_settings,.st-key-header_power) {
    flex:0 0 52px !important; width:52px !important; min-width:52px !important; max-width:52px !important;
}
:is(.st-key-header_settings,.st-key-header_power) button {
    box-sizing:border-box !important; flex:0 0 52px !important;
    width:52px !important; min-width:52px !important; max-width:52px !important;
    height:52px !important; min-height:52px !important; max-height:52px !important;
    aspect-ratio:1 / 1 !important; border-radius:50% !important; padding:0 !important;
}
.st-key-common_header .st-key-status_bolt { flex:0 0 52px !important; min-width:52px !important; }
.st-key-dashboard_header { padding-top:0 !important; }
@media(max-width:600px) {
    .st-key-common_header { gap:12px !important; }
    .st-key-common_header .brand-name { font-size:clamp(14px,3.2vw,22px) !important; line-height:28px !important; }
    .st-key-common_header .brand-sub { font-size:11px !important; }
    .st-key-common_header .st-key-user_brand { gap:8px !important; }
}

.stage-mode { font-size:11px; color:#596C7B; padding:3px 6px; border-radius:5px; background:#EDF2F5; }
.stage-detail { color:#687887; font-size:13px; line-height:1.65; margin:8px 0 12px; min-height:44px; }
.stage-evidence { font-size:13px; color:#385970; }
.stage-evidence.pending { color:#7D8995; }
.deployment-checks { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.deployment-check { padding:16px; border:1px solid #E0E6EB; border-radius:10px; background:#FAFBFC; }
.check-top { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:15px; }
.check-top span { color:#687581; font-size:12px; background:#EBEFF2; padding:4px 8px; border-radius:6px; }
.check-detail { margin-top:9px; color:#657585; font-size:13px; line-height:1.65; }
@media(max-width:760px) { .deployment-checks { grid-template-columns:1fr; } }

.result-count { font-size:19px; font-weight:750; color:#202830; line-height:1.5; padding-top:20px; }
.st-key-result_facility [data-baseweb="select"] > div { min-height:42px; border:1px solid #D5DCE3; border-radius:10px; background:#F6F8FA; }
.st-key-result_facility [data-testid="stWidgetLabel"] p { font-size:13px; color:#657180; }
</style>
"""

MAP_CSS = """
<style>
@font-face{font-family:'Pretendard Variable';src:url('/app/static/fonts/PretendardVariable.woff2') format('woff2');font-weight:45 920;font-display:swap}body{margin:0;font-family:'Pretendard Variable','Malgun Gothic',sans-serif}.map-shell{position:relative;height:525px;overflow:hidden;border:1px solid #DCE8E5;border-radius:21px;background:#F2F7F2}.map-grid{position:absolute;inset:0;background:linear-gradient(112deg,transparent 37%,#DCEEF2 37%,#DCEEF2 47%,transparent 47%),linear-gradient(0deg,transparent 39%,#FFF 39%,#FFF 40%,transparent 40%),linear-gradient(90deg,transparent 61%,#FFF 61%,#FFF 62%,transparent 62%),#F3F7F3}.map-label{position:absolute;top:14px;left:14px;z-index:5;max-width:78%;padding:8px 11px;border-radius:9px;background:#FFF;box-shadow:0 2px 10px #1232;color:#51412B;font-size:12px}.radius-ring{position:absolute;width:45%;aspect-ratio:1;left:27.5%;top:28%;border:2px dashed #C3922E;background:#F6D66F24;border-radius:50%}.center-dot{position:absolute;left:50%;top:50%;width:14px;height:14px;transform:translate(-50%,-50%);border:2px solid #FFF;border-radius:5px;background:#3A2D1B}.map-marker{position:absolute;z-index:3;transform:translate(-50%,-50%)}.map-marker:hover,.map-marker:focus-within{z-index:10}.map-pin{width:37px;height:37px;border:2px solid #FFF;border-radius:50%;background:#40331D;box-shadow:0 2px 6px #0003;color:#FFF;cursor:pointer;font-weight:800}.map-pop{visibility:hidden;opacity:0;position:absolute;left:50%;bottom:calc(100% + 9px);width:240px;transform:translateX(-50%);padding:13px;border:1px solid #DEE5EA;border-radius:13px;background:#FFF;box-shadow:0 10px 28px #2433422B;color:#26313C;transition:.14s}.map-marker:hover .map-pop,.map-marker:focus-within .map-pop,.map-marker.open .map-pop{visibility:visible;opacity:1}.map-pop-title{font-size:13px;font-weight:800;margin-bottom:8px}.map-pop-row{display:flex;justify-content:space-between;gap:8px;padding:3px 0;font-size:11px}.map-pop-row span{color:#778490}.map-pop-row b{text-align:right}.map-pop-note{margin-top:7px;padding-top:7px;border-top:1px solid #EDF0F2;color:#8A959F;font-size:10px;line-height:1.4}.map-legend{position:absolute;left:14px;bottom:14px;z-index:5;padding:9px 11px;border-radius:9px;background:#FFF;color:#5A472D;font-size:12px;box-shadow:0 2px 10px #1232}
.map-hover{visibility:hidden;opacity:0;position:absolute;left:50%;bottom:calc(100% + 9px);width:170px;transform:translateX(-50%);padding:9px 10px;border:1px solid #DEE5EA;border-radius:10px;background:#FFF;box-shadow:0 7px 20px #24334222;color:#26313C;font-size:11px}.map-hover b{display:block;font-size:12px;margin-bottom:4px}.map-hover span{color:#526270;font-weight:750}.map-marker:hover .map-hover,.map-marker:focus-within .map-hover{visibility:visible;opacity:1}.map-marker:hover .map-pop,.map-marker:focus-within .map-pop{visibility:hidden;opacity:0}.map-marker.open .map-pop{visibility:visible;opacity:1}.map-marker.open .map-hover{visibility:hidden;opacity:0}
.map-footer{padding:10px 4px 0;color:#657180;font-size:12px;line-height:1.6;font-family:"Pretendard Variable","Malgun Gothic",sans-serif}.map-legend{max-width:calc(100% - 52px);line-height:1.5;pointer-events:none}.map-conditions{font-size:12px;font-weight:700;color:#303A44;margin-bottom:3px}.map-legend-help{font-size:11px;color:#657180}</style>
"""


def init_state() -> None:
    defaults: dict[str, Any] = {
        "role": None, "auth_token": None, "view": "search", "mode": "탐색", "results": [], "request": None,
        "chat": [{"role": "assistant", "content": "안녕하세요, 차지핀이에요. 서울의 충전할 장소를 말씀해 주세요. (챗봇 설정 범위 1km)"}],
        "pending_plan": None, "notice": None, "quality_notices": [], "booted": False, "place_query": "",
        "place_suggestions": [], "suggestion_query": "", "suggestion_error": None, "selected_place": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def is_residential_station(station: dict[str, Any]) -> bool:
    # Use explicit facility/name evidence; brand names alone do not prove residential use.
    text = " ".join(str(station.get(key) or "") for key in ("facility_type", "name"))
    normalized = "".join(text.casefold().split())
    return any(word in normalized for word in ("아파트", "공동주택", "주거시설", "주거용", "apartment"))


def set_search_response(payload: dict[str, Any]) -> None:
    st.session_state.results = [item for item in payload.get("results", []) if not is_residential_station(item)]
    st.session_state.result_page = 0
    st.session_state.selected_station_id = None
    st.session_state.request = payload.get("applied_request")
    st.session_state.pending_plan = None
    findings = payload.get("critic_findings") or []
    st.session_state.quality_notices = [str(item) for item in findings if item]
    st.session_state.notice = None


def access_token() -> str:
    return str(st.session_state.auth_token or "")


def load_default_once() -> None:
    if st.session_state.booted or not access_token():
        return
    st.session_state.booted = True
    try:
        set_search_response(API.default_search(access_token()))
    except ApiError as error:
        st.session_state.notice = error.message


def role_dialog(title: str, body: str) -> None:
    @st.dialog(title)
    def _dialog() -> None:
        st.write(body)
        if st.button("확인", use_container_width=True):
            st.rerun()
    _dialog()


def render_login() -> None:
    with st.container(key="login_layout"):
        visual, center = st.columns([1.06, 1], vertical_alignment="center", gap="large")
        with visual:
            with st.container(key="login_visual"):
                st.image(str(Path(__file__).resolve().parent / "static" / "chargepin-entry-car.png"),
                         caption=None, width="stretch")
        with center:
            st.markdown('<div class="brand-row"><div class="brand-bolt">⚡</div><div><div class="brand-name">ChargePin</div><div class="brand-sub">서울 전기차 충전소 안내</div></div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login-form", clear_on_submit=True):
                st.markdown("### 차지핀 시작하기")
                service_key = st.text_input("접속 코드", type="password", placeholder="접속 코드를 입력해주세요", label_visibility="collapsed")
                submitted = st.form_submit_button("접속하기", type="primary", use_container_width=True)
            if submitted:
                if not service_key.strip():
                    st.warning("접속 코드를 입력해주세요.")
                    return
                try:
                    session = API.login(service_key)
                    st.session_state.auth_token = session["access_token"]
                    st.session_state.role = ROLE_LABELS.get(session["role"], "손님")
                    st.session_state.booted = False
                    st.session_state.notice = None
                    st.rerun()
                except ApiError as error:
                    st.error(error.message)


def logout() -> None:
    st.session_state["_purge_on_logout"] = True
    st.rerun()



def availability_label(station: dict[str, Any]) -> str:
    return station.get("availability", {}).get("label", "충전 상태 확인 불가")


def map_html(results: list[dict[str, Any]], request: dict[str, Any] | None) -> str:
    positions = ((34, 37), (65, 34), (31, 62), (68, 61), (52, 46))
    markers: list[str] = []
    for index, station in enumerate(results):
        left, top = positions[index % len(positions)]
        availability = station.get("availability", {})
        parking = station.get("parking_free")
        parking_text = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "주차 정보 확인 필요"
        connector_text = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "타입 확인 필요"
        pop_rows = "".join((
            f'<div class="map-pop-row"><span>시설 유형</span><b>{escape(station.get("facility_type", "확인 필요"))}</b></div>',
            f'<div class="map-pop-row"><span>충전기</span><b>{escape(connector_text)}</b></div>',
            f'<div class="map-pop-row"><span>충전 상태</span><b>{escape(availability_label(station))}</b></div>',
            f'<div class="map-pop-row"><span>이용 시간</span><b>{escape(station.get("use_time") or "확인 필요")}</b></div>',
            f'<div class="map-pop-row"><span>주차</span><b>{parking_text}</b></div>',
        ))
        name = escape(station.get("name", "충전소"))
        availability_text = escape(availability_label(station))
        markers.append(
            f'<div class="map-marker" style="left:{left}%;top:{top}%"><button class="map-pin" onclick="this.parentElement.classList.toggle(\'open\')" aria-label="{name} 상세 보기">⚡</button><div class="map-hover"><b>{name}</b><span>{availability_text}</span></div><div class="map-pop"><div class="map-pop-title">{name}</div>{pop_rows}<div class="map-pop-note">환경공단 상태 · {escape(str(station.get("reported_at") or "갱신 시각 확인 필요"))}</div></div></div>'
        )
    condition_badge = ""
    if request:
        selected_types = "·".join("급속" if value == "FAST" else "완속" for value in request.get("connector_types", []))
        condition_badge = '<div class="map-conditions">반경 ' + escape(str(request.get("radius_km", 3))) + ' km · ' + escape(selected_types or "전체 타입") + '</div>'
    applied = request or {}
    center = applied.get("center", {})
    source = center.get("source", "")
    label = "강남역 기준" if source == "initial_default" else "선택한 위치 기준" if request else "장소명을 입력해 주세요"
    javascript_key = os.environ.get("KAKAO_JAVASCRIPT_KEY", "").strip().strip("\"").strip("'")
    fallback_html = f'<div id="map-fallback" style="position:absolute;inset:0"><div class="map-grid"></div><div class="radius-ring"></div><div class="center-dot"></div>{"".join(markers)}</div>'
    if javascript_key:
        station_payload: list[dict[str, Any]] = []
        for station in results:
            location = station.get("location", {})
            try:
                latitude, longitude = float(location["lat"]), float(location["lng"])
            except (KeyError, TypeError, ValueError):
                continue
            availability = availability_label(station)
            types = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "타입 확인 필요"
            parking = station.get("parking_free")
            parking_text = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "주차 정보 확인 필요"
            detail = (
                f'<div class="map-pop-title">{escape(station.get("name", "충전소"))}</div>'
                f'<div class="map-pop-row"><span>주소</span><b>{escape(str(station.get("address") or "확인 필요"))}</b></div>'
                f'<div class="map-pop-row"><span>시설 유형</span><b>{escape(str(station.get("facility_type") or "확인 필요"))}</b></div>'
                f'<div class="map-pop-row"><span>충전기</span><b>{escape(types)}</b></div>'
                f'<div class="map-pop-row"><span>충전 상태</span><b>{escape(availability)}</b></div>'
                f'<div class="map-pop-row"><span>이용 시간</span><b>{escape(station.get("use_time") or "확인 필요")}</b></div>'
                f'<div class="map-pop-row"><span>주차</span><b>{parking_text}</b></div>'
                f'<div class="map-pop-row"><span>이용 제한</span><b>{escape(str(station.get("restriction_detail") or "확인 필요"))}</b></div>'
                f'<div class="map-pop-row"><span>상태 갱신</span><b>{escape(str(station.get("reported_at") or "확인 필요"))}</b></div>'
            )
            station_payload.append({"lat": latitude, "lng": longitude, "name": station.get("name", "충전소"), "summary": availability, "detail": detail})
        stations_json = json.dumps(station_payload, ensure_ascii=False).replace("</", "<\\/")
        center_lat = center.get("lat", 37.4980)
        center_lng = center.get("lng", 127.0270)
        return MAP_CSS + f'''<div class="map-shell">{fallback_html}<div id="kakao-map" style="position:absolute;inset:0"></div><div class="map-legend">{condition_badge}<div class="map-legend-help">⚡ 충전소 · hover 요약 / click 상세 정보</div></div></div><div id="map-status" class="map-footer">{label} · 카카오 지도 · 충전 상태는 환경공단 API 기준입니다.</div><script>const stations={stations_json};const fallback=document.getElementById('map-fallback');const statusLabel=document.getElementById('map-status');let mapReady=false;function showFallback(message){{document.getElementById('kakao-map').style.display='none';fallback.style.display='block';statusLabel.innerHTML=message;}}function renderKakaoMap(){{try{{const maps=window.kakao.maps;const map=new maps.Map(document.getElementById('kakao-map'),{{center:new maps.LatLng({center_lat},{center_lng}),level:6}});stations.forEach(function(item){{const marker=new maps.Marker({{position:new maps.LatLng(item.lat,item.lng),map:map}});const info=new maps.InfoWindow({{removable:true}});maps.event.addListener(marker,'mouseover',function(){{info.setContent('<div class="map-hover" style="visibility:visible;opacity:1;position:static;transform:none"><b>'+item.name+'</b><span>'+item.summary+'</span></div>');info.open(map,marker);}});maps.event.addListener(marker,'mouseout',function(){{info.close();}});maps.event.addListener(marker,'click',function(){{info.setContent('<div class="map-pop" style="visibility:visible;opacity:1;position:static;transform:none">'+item.detail+'</div>');info.open(map,marker);}});}});mapReady=true;fallback.style.display='none';}}catch(error){{showFallback('카카오 지도 초기화에 실패했습니다.<br>카카오 콘솔에 http://127.0.0.1:8501 을 등록해 주세요.');}}}}const sdk=document.createElement('script');sdk.src='https://dapi.kakao.com/v2/maps/sdk.js?appkey={escape(javascript_key)}&autoload=false';sdk.onload=function(){{if(window.kakao&&window.kakao.maps){{window.kakao.maps.load(renderKakaoMap);}}else{{showFallback('카카오 지도 SDK를 불러오지 못했습니다. JavaScript 키를 확인해 주세요.');}}}};sdk.onerror=function(){{showFallback('카카오 지도 SDK 연결에 실패했습니다. JavaScript 키와 등록 도메인을 확인해 주세요.');}};document.head.appendChild(sdk);window.setTimeout(function(){{if(!mapReady){{showFallback('카카오 지도 연결을 기다리고 있습니다.<br>카카오 콘솔에 http://127.0.0.1:8501 을 등록해 주세요.');}}}},7000);</script>'''
    return MAP_CSS + f'<div class="map-shell">{fallback_html}<div class="map-legend">{condition_badge}<div class="map-legend-help">⚡ 충전소 · hover 요약 / click 상세 정보</div></div></div><div class="map-footer">{label} · 예시 지도 · 실제 카카오 지도 키·도메인 연결 전 화면입니다.</div>'


def render_station_cards(results: list[dict[str, Any]]) -> None:
    if not results:
        st.markdown('<div class="cp-result-empty">조건에 맞는 충전소가 없어요.<br>장소나 검색 조건을 바꿔 보세요.</div>', unsafe_allow_html=True)
        return
    page_size = 10
    page_count = (len(results) + page_size - 1) // page_size
    page = max(0, min(st.session_state.get("result_page", 0), page_count - 1))
    st.session_state.result_page = page
    with st.container(height=410, border=False, key="result_scroll"):
        for index, station in enumerate(results[page * page_size:(page + 1) * page_size], start=page * page_size):
            facility_id = str(station.get("facility_id") or "")
            with st.container(border=True, key=f"result_item_{index}"):
                if st.button(str(station.get("name") or "충전소"), key=f"focus_station_{index}",
                             width="stretch", help="지도에서 이 충전소 보기"):
                    st.session_state.selected_station_id = facility_id or None
                    st.rerun()
                st.caption(str(station.get("address") or "주소 확인 필요"))
                types = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "속도 확인 필요"
                distance = station.get("distance_km")
                distance_text = f"직선 {distance:.1f} km" if isinstance(distance, (int, float)) else "거리 확인 필요"
                state = (station.get("availability") or {}).get("state")
                tone = "ok" if state == "AVAILABLE" else "warn" if state == "DELAYED" else ""
                parking = station.get("parking_free")
                parking_text = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "주차 확인 필요"
                access_text = "외부인 " + outsider_access(station)
                chips = [(types, "speed"), (distance_text, "distance"), (parking_text, "ok" if parking is True else "warn"), (access_text, "ok" if outsider_access(station) == "가능" else "warn"),
                         (availability_label(station), tone)]
                st.markdown('<div class="cp-result-meta">' + "".join(
                    '<span class="cp-result-chip ' + escape(tone_name) + '">' + escape(str(text)) + '</span>'
                    for text, tone_name in chips) + '</div>', unsafe_allow_html=True)
    if page_count > 1:
        with st.container(key="results_pager", horizontal=True, horizontal_alignment="center", vertical_alignment="center"):
            if st.button("이전", disabled=page == 0, key="results_previous"):
                st.session_state.result_page = page - 1
                st.rerun()
            st.markdown(f'<div class="result-page">{page + 1} / {page_count}</div>', unsafe_allow_html=True)
            if st.button("다음", disabled=page == page_count - 1, key="results_next"):
                st.session_state.result_page = page + 1
                st.rerun()


def choose_sidebar_place(candidate: dict[str, Any]) -> None:
    st.session_state.selected_place = candidate
    st.session_state.place_query = candidate["name"]
    st.session_state.suggestion_query = candidate["name"]
    st.session_state.place_suggestions = []
    st.session_state.suggestion_error = None


def search_payload(place: dict[str, Any], radius: int, connector_labels: list[str]) -> dict[str, Any]:
    location = place["location"]
    region_filters = [f"zscode:{place['district_code']}"] if place.get("district_code") else []
    return {
        "center": {"lat": location["lat"], "lng": location["lng"], "source": "kakao_candidate"},
        "radius_km": radius,
        "connector_types": [CONNECTOR_CODES[item] for item in connector_labels],
        "region_filters": region_filters,
    }


FACILITY_GROUPS = {
    "휴게시설": ("휴게",),
    "주차시설": ("주차",),
    "공공기관·공공장소": ("공공", "공공기관",),
    "숙박시설": ("숙박",),
    "관광·문화시설": ("관광", "문화", "교육문화"),
    "골프·스포츠": ("골프", "스포츠", "체육"),
    "쇼핑시설": ("쇼핑", "백화점", "대형마트",),
}


def outsider_access(station: dict[str, Any]) -> str:
    detail = "".join(str(station.get("restriction_detail") or "").split())
    # Missing/ambiguous restriction text never establishes public access.
    negative = ("외부인출입불가", "외부인출입제한", "외부인이용불가", "입주민전용", "거주자전용",
                "입주자전용", "관계자외출입금지", "직원전용", "거주자외출입제한")
    if any(word in detail for word in negative):
        return "불가"
    if any(word in detail for word in ("조건부", "사전", "문의", "허가", "승인", "고객전용", "이용제한")):
        return "확인 필요"
    if any(word in detail for word in ("외부인이용가능", "외부인출입가능", "누구나이용", "일반인개방", "상시개방", "이용제한없음", "제한없음")):
        return "가능"
    return "확인 필요"


def filter_exploration_results(results: list[dict[str, Any]], facilities: list[str],
                               access: str, parking: str) -> list[dict[str, Any]]:
    filtered = []
    for item in results:
        if is_residential_station(item):
            continue
        facility = str(item.get("facility_type") or "")
        if facilities and set(facilities) != set(FACILITY_GROUPS) and not any(any(word in facility for word in FACILITY_GROUPS[group]) for group in facilities):
            continue
        if access != "전체" and outsider_access(item) != access:
            continue
        free = item.get("parking_free")
        if parking == "무료" and free is not True:
            continue
        if parking == "무료 아님" and free is not False:
            continue
        if parking == "확인 필요" and free is not None:
            continue
        filtered.append(item)
    return filtered


def apply_search_radius(payload: dict[str, Any], center: dict[str, Any], radius_km: float) -> dict[str, Any]:
    """Apply exact client radius after querying a supported enclosing server radius."""
    filtered = []
    lat, lng = radians(float(center["lat"])), radians(float(center["lng"]))
    for item in payload.get("results", []):
        location = item.get("location") or {}
        try:
            other_lat, other_lng = radians(float(location["lat"])), radians(float(location["lng"]))
        except (KeyError, TypeError, ValueError):
            continue
        arc = sin((other_lat - lat) / 2) ** 2 + cos(lat) * cos(other_lat) * sin((other_lng - lng) / 2) ** 2
        distance = 6371.0088 * 2 * asin(sqrt(min(1.0, max(0.0, arc))))
        if distance <= radius_km:
            filtered.append(dict(item, distance_km=round(distance, 2)))
    applied = dict(payload.get("applied_request") or {})
    applied["server_radius_km"] = applied.get("radius_km")
    applied["radius_km"] = radius_km
    return dict(payload, results=sorted(filtered, key=lambda item: item["distance_km"]), applied_request=applied)


def render_direct_search() -> None:
    st.markdown('<div class="cp-search-title">충전소 찾기</div>', unsafe_allow_html=True)
    st.markdown('<div class="cp-search-space"></div>', unsafe_allow_html=True)
    query = st.text_input("장소검색", placeholder="장소명 입력 (예: 강남역, 서울시청)", key="place_query")
    normalized_query = query.strip()
    if normalized_query != st.session_state.suggestion_query:
        st.session_state.suggestion_query = normalized_query
        st.session_state.selected_place = None
        st.session_state.place_suggestions = []
        st.session_state.suggestion_error = None
        if len(normalized_query) >= 2:
            try:
                st.session_state.place_suggestions = API.suggest_places(normalized_query, access_token())
            except ApiError as error:
                st.session_state.suggestion_error = error.message
    if normalized_query and len(normalized_query) < 2:
        st.caption("장소명을 두 글자 이상 입력해 주세요.")
    if st.session_state.suggestion_error:
        st.caption(f"장소 후보를 가져오지 못했어요: {st.session_state.suggestion_error}")
    elif st.session_state.place_suggestions:
        for candidate in st.session_state.place_suggestions:
            st.button(f"{candidate['name']} · {candidate['address']}",
                      key=f"sidebar-place-{candidate['candidate_id']}", use_container_width=True,
                      on_click=choose_sidebar_place, args=(candidate,))
    selected_place = st.session_state.selected_place
    if selected_place:
        st.caption(f"선택한 장소 · {selected_place['name']} · {selected_place['address']}")
    speed = st.radio("충전 속도", ["전체", "급속", "완속"], horizontal=True, key="charging_speed")
    connector_labels = ["급속", "완속"] if speed == "전체" else [speed]
    with st.expander("상세 조건", expanded=False):
        st.multiselect("충전소 분류", list(FACILITY_GROUPS), default=list(FACILITY_GROUPS), key="facility_groups",
                       placeholder="전체 장소", help="분류가 확인된 결과만 표시합니다. 주거용 아파트는 제외합니다.")
        st.radio("외부인 이용", ["전체", "가능", "불가", "확인 필요"], horizontal=True, key="outsider_filter")
        st.radio("주차 요금", ["전체", "무료", "무료 아님", "확인 필요"], horizontal=True, key="parking_filter",
                 help="충전 요금과 별도입니다. 무료가 아닌 경우 실제 금액은 확인이 필요합니다.")
        radius_choice = st.radio("검색 범위", [1, 2, 3], horizontal=True,
                                 format_func=lambda value: f"{value} km", key="search_diameter",
                                 help="표시된 값의 절반을 반경으로 검색합니다: 반경 0.5·1·1.5km.")
    search_col, refresh_col = st.columns([5, 1], vertical_alignment="bottom")
    with search_col:
        search_clicked = st.button("충전소 검색", type="primary", use_container_width=True)
    with refresh_col:
        refresh_clicked = st.button("↻", help="충전소 다시 검색", use_container_width=True)
    if search_clicked or refresh_clicked:
        if selected_place is None:
            st.warning("장소명을 입력한 뒤 카카오 장소 후보를 선택해 주세요.")
            return
        radius = radius_choice / 2
        try:
            response = API.search(search_payload(selected_place, radius, connector_labels), access_token())
            set_search_response(apply_search_radius(response, selected_place["location"], radius))
            st.rerun()
        except ApiError as error:
            st.error(error.message)


def complete_chat_search(plan: dict[str, Any]) -> None:
    candidate_id = plan.get("suggested_candidate_id")
    candidates = plan.get("candidates", [])
    if plan.get("status") == "AWAITING_LOCATION_CONFIRMATION" and not candidate_id:
        candidate_id = candidates[0]["candidate_id"] if candidates else None
        if not candidate_id:
            st.session_state.pending_plan = None
            st.session_state.chat.append({"role": "assistant", "content": "검색할 장소를 찾지 못했어요. 역 이름이나 주소를 알려주세요."})
            return
    st.session_state.pending_plan = None
    response = API.confirm(plan["request_id"], access_token(), candidate_id)
    last_message = next((str(item.get("content", "")) for item in reversed(st.session_state.chat)
                         if item.get("role") == "user"), "")
    explicit_distance = re.search(r"\d+(?:\.\d+)?\s*(?:km|킬로미터|킬로|키로|미터|m\b)", last_message, re.IGNORECASE)
    applied = response.get("applied_request") or {}
    center = applied.get("center") or {}
    try:
        server_radius = float(applied.get("radius_km", 0))
    except (TypeError, ValueError):
        server_radius = 0
    if not explicit_distance and server_radius > 0.5 and "lat" in center and "lng" in center:
        response = apply_search_radius(response, center, 0.5)
    set_search_response(response)
    selected = next((item for item in candidates if item["candidate_id"] == candidate_id), None)
    location = f"{selected['name']} 주변" if selected else "입력한 지역 주변"
    count = len(st.session_state.results)
    if response.get("status") == "degraded":
        findings = response.get("critic_findings") or []
        details = "\n".join(f"- {finding}" for finding in findings)
        message = f"{location} 검색 결과 {count}곳을 표시합니다."
        message += f"\n\n확인하지 못한 정보:\n{details}" if details else "\n\n일부 정보를 확인하지 못했지만, 상세 사유는 제공되지 않았어요."
    elif count:
        message = f"{location} 충전소 {count}곳을 찾았어요."
    else:
        message = f"{location}에서 조건에 맞는 충전소를 찾지 못했어요."
    st.session_state.chat.append({"role": "assistant", "content": message})


def render_chat() -> None:
    size = st.session_state.get("chat_panel_state", "compact")
    if size == "collapsed":
        with st.container(key="chat_launcher"):
            if st.button("AI 챗", icon=":material/bolt:", key="chat_open"):
                st.session_state.chat_panel_state = "compact"
                st.rerun()
        return
    with st.container(key=f"floating_chat_{size}"):
        with st.container(key="chat_header", horizontal=True, vertical_alignment="center", gap="small"):
            st.markdown('<div class="cp-chat-title"><span>✦</span> AI 챗</div>', unsafe_allow_html=True, width="stretch")
            resize_label = "대화창 줄이기" if size == "expanded" else "대화창 넓히기"
            if st.button(resize_label, icon=":material/close_fullscreen:" if size == "expanded" else ":material/open_in_full:",
                         key="chat_expand", help=resize_label, width=36):
                st.session_state.chat_panel_state = "compact" if size == "expanded" else "expanded"
                st.rerun()
            if st.button("대화창 접기", icon=":material/remove:", key="chat_collapse", help="대화창 접기", width=36):
                st.session_state.chat_panel_state = "collapsed"
                st.rerun()
        with st.container(height=420 if size == "expanded" else 250, border=False,
                          key="chat_history", autoscroll=True):
            for item in st.session_state.chat:
                with st.chat_message(item["role"], avatar="⚡" if item["role"] == "assistant" else "👤"):
                    st.markdown(item["content"])
        pending = st.session_state.pending_plan
        if pending and pending.get("status") in ("AWAITING_CONFIRMATION", "AWAITING_LOCATION_CONFIRMATION"):
            try:
                complete_chat_search(pending)
                st.session_state.reset_search_filters = True
            except ApiError as error:
                st.session_state.chat.append({"role": "assistant", "content": error.message})
            st.rerun()
        prompt = st.chat_input("강남역처럼 장소만 입력해도 가능해요", key="floating_chat_input")
        if prompt:
            st.session_state.chat.append({"role": "user", "content": prompt})
            try:
                response = API.plan(prompt, access_token())
                if response.get("status") in ("AWAITING_CONFIRMATION", "AWAITING_LOCATION_CONFIRMATION"):
                    complete_chat_search(response)
                    st.session_state.reset_search_filters = True
                else:
                    st.session_state.pending_plan = None
                    st.session_state.chat.append({"role": "assistant", "content": response["message"]})
            except ApiError as error:
                st.session_state.chat.append({"role": "assistant", "content": error.message})
            st.rerun()


def render_status_demo() -> None:
    labels = {1: "결과 없음", 2: "정보 지연", 3: "요청 제한", 4: "제공자 인증 만료", 5: "AI 챗 연결 실패"}
    with st.popover("상태 시연", icon=":material/bolt:", help="상태 시연", key="status_bolt"):
        st.caption("테스트 전용 · 사용자 화면 상태")
        scenario = st.selectbox("시나리오", list(labels), format_func=lambda item: f"{labels[item]} · boom/{item}")
        if st.button("상태 적용", use_container_width=True):
            try:
                payload = API.boom(scenario, access_token())
                level = st.info if scenario in (1, 2, 4) else st.warning
                level(f"[시연] {payload['code']} · {payload['message']}")
            except ApiError as error:
                payload = error.payload or {}
                st.error(f"[시연] {payload.get('code', 'ERROR')} · {error.message}")


def render_header(dashboard_view: bool = False, navigation: Any = None) -> str | None:
    # The shared row keeps the brand and action icons in the same positions.
    menu = None
    with st.container(key="common_header", horizontal=True, vertical_alignment="center", gap="medium"):
        name = "ChargePin 운영 대시보드" if dashboard_view else "ChargePin"
        subtitle = "에이전트 운영 · 가드레일 · 컴플라이언스" if dashboard_view else "서울 전기차 충전소 안내"
        with st.container(key="user_brand", horizontal=True, vertical_alignment="center", gap="small", width="stretch"):
            render_status_demo()
            marker = '<span class="dashboard-marker" aria-hidden="true"></span>' if dashboard_view else ""
            st.markdown(
                '<div class="cp-brand-copy">' + marker + '<div class="brand-name">' + name + '</div><div class="brand-sub">' + subtitle + '</div></div>',
                unsafe_allow_html=True, width="content",
            )
        if navigation is not None:
            with st.container(key="header_navigation", horizontal=True, vertical_alignment="center",
                              gap="medium", width="stretch"):
                menu = navigation()
        with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center",
                          gap="small", key="header_actions", width=116):
            destination = "사용자 화면" if dashboard_view else "운영 대시보드"
            if st.button(destination, icon=":material/home:" if dashboard_view else ":material/settings:", width=52, key="header_settings", help=destination):
                if not dashboard_view and not can_view_dashboard(st.session_state.role):
                    role_dialog("관리자 전용 화면입니다.", "관리자만 운영 대시보드를 이용할 수 있습니다.")
                else:
                    st.session_state.view = "search" if dashboard_view else "dashboard"
                    st.rerun()
            if st.button("로그아웃", icon=":material/power_settings_new:", width=52, key="header_power", help="로그아웃"):
                logout()

    return menu


def provider_states() -> list[tuple[str, str]]:
    events = st.session_state.get("api_events", [])
    map_status = "지도 키 설정됨 · 브라우저 로딩 별도" if os.environ.get("KAKAO_JAVASCRIPT_KEY", "").strip() else "지도 키 미설정"
    places = [event for event in events if event.get("place_lookup") == "success" or event.get("path") == "/places/suggest"]
    if places:
        latest = places[-1]
        place_status = "최근 장소 조회 응답 수신" if latest["outcome"] == "success" else "최근 장소 요청 실패"
        place_status += f" · {latest['elapsed_ms']} ms"
    elif st.session_state.place_suggestions or st.session_state.selected_place:
        place_status = "장소 후보 수신 · 이전 세션 이력 미수집"
    else:
        place_status = "이 세션의 장소 조회 기록 없음"
    searches = [event for event in events if "search_status" in event]
    if searches:
        charger_status = "검색 응답 수신" if searches[-1]["search_status"] == "completed" else "검색 응답 수신 · 일부 확인 불가"
        charger_status += " · 원천 상태는 결과 참조"
    elif st.session_state.request is not None:
        charger_status = "검색 결과 있음 · 이전 요청 이력 미수집"
    else:
        charger_status = "이 세션의 검색 응답 기록 없음"
    return [("카카오 지도", map_status), ("카카오 장소", place_status),
            ("환경공단 충전기", charger_status), ("환경공단 캐시", "백엔드 캐시 사용 · 상태는 서버 집계 연결 대기")]


def dashboard_empty(message: str) -> None:
    st.markdown('<div class="dashboard-empty"><span class="pending-dot"></span>' + escape(message) + '</div>', unsafe_allow_html=True)


def dashboard_pending_rows(labels: list[str]) -> None:
    for label in labels:
        st.markdown('<div class="detail-row"><span>' + escape(label) + '</span><b>연결 대기</b></div>', unsafe_allow_html=True)

def render_instrument_cluster(health_text: str) -> None:
    gauges = []
    for title, value, unit, live in [
        ("백엔드", health_text, "실시간 연결 상태", True),
        ("요청 성공률", "—", "% · 연결 대기", False),
        ("재시도율", "—", "% · 연결 대기", False),
        ("최근 배포", "—", "이력 연결 대기", False),
    ]:
        ticks = []
        for index in range(17):
            angle = radians(180 + index * 180 / 16)
            inner = 65 if index % 4 == 0 else 69
            ticks.append(f'<line x1="{100 + inner * cos(angle):.2f}" y1="{100 + inner * sin(angle):.2f}" x2="{100 + 76 * cos(angle):.2f}" y2="{100 + 76 * sin(angle):.2f}" stroke="#77828E" stroke-width="1.5"/>')
        tone = "live" if live and health_text == "정상" else "fault" if live else "waiting"
        gauges.append(
            '<div class="instrument"><div class="instrument-label"><i class="instrument-led ' + tone + '"></i>'
            + escape(title) + '</div><svg viewBox="0 0 200 140" role="img" aria-label="' + escape(title + " " + value)
            + '"><path d="M 16 100 A 84 84 0 0 1 184 100" fill="none" stroke="#46515D" stroke-width="3"/>'
            + "".join(ticks) + '<text x="100" y="99" text-anchor="middle" fill="#F7F9FC" font-size="'
            + ("22" if live else "32") + '" font-weight="700">' + escape(value)
            + '</text><text x="100" y="126" text-anchor="middle" fill="#ACB8C6" font-size="11">'
            + escape(unit) + '</text></svg></div>'
        )
    st.markdown(
        '<section class="instrument-cluster"><div class="cluster-heading"><span>시스템 모니터</span>'
        '<span class="cluster-source">백엔드 상태 실측 · 운영 지표 연결 대기</span></div><div class="instrument-grid">'
        + "".join(gauges) + '</div></section>', unsafe_allow_html=True,
    )


def dashboard_heading(title: str) -> None:
    st.markdown('<div class="console-heading"><span class="console-indicator"></span><h4>'
                + escape(title) + '</h4></div>', unsafe_allow_html=True)


def load_deployment_reference() -> dict[str, Any]:
    return json.loads(Path(__file__).with_name("deployment_reference.json").read_text(encoding="utf-8"))


def render_deployment_stages(reference: dict[str, Any]) -> None:
    stages = []
    for index, stage in enumerate(reference["stages"], start=1):
        evidence = ('<a class="stage-evidence" href="' + escape(stage["url"], quote=True)
                    + '" target="_blank" rel="noopener noreferrer">실행 기록 ↗</a>') if stage.get("url") else '<span class="stage-evidence pending">관리표 기록</span>'
        stages.append('<div class="deployment-stage"><div class="stage-top"><span class="stage-index">'
                      + f"{index:02d}" + '</span><span class="stage-mode">' + escape(stage["mode"])
                      + '</span></div><div class="stage-title">' + escape(stage["title"])
                      + '</div><div class="stage-status">' + escape(stage["status"])
                      + '</div><div class="stage-detail">' + escape(stage["detail"]) + '</div>' + evidence + '</div>')
    st.markdown('<div class="deployment-stages">' + "".join(stages) + '</div>', unsafe_allow_html=True)


def render_deployment_checks(reference: dict[str, Any]) -> None:
    rows = []
    for check in reference["checks"]:
        rows.append('<div class="deployment-check"><div class="check-top"><b>' + escape(check["title"])
                    + '</b><span>' + escape(check["status"]) + '</span></div><div class="check-detail">'
                    + escape(check["detail"]) + '</div></div>')
    st.markdown('<div class="deployment-checks">' + "".join(rows) + '</div>', unsafe_allow_html=True)



def render_dashboard() -> None:
    # Menus are owned by dashboard_view.MENUS; legacy names from older sessions fall back to the overview.
    if st.session_state.get("dashboard_navigation") not in DASHBOARD_MENUS:
        st.session_state.dashboard_navigation = DASHBOARD_MENUS[0]
    # Server views (ops summary · platform · Auto Healing) switch on with one environment
    # variable once the backend serves them (handoff/2026-11-08/BACKEND_HANDOFF.md).
    # Until then every server panel shows "연결 대기".
    loaders: dict[str, Any] = {}
    if os.environ.get("CHARGEPIN_DASHBOARD_SERVER_OPS", "").strip().lower() == "true":
        token = access_token()
        loaders = {
            "server_summary_loader": lambda: API.ops_summary(token),
            "platform_loader": lambda: API.ops_platform(token),
            "healing_loader": lambda: API.ops_healing(token),
        }
    render_operations_dashboard(API, render_header, provider_states, load_deployment_reference, **loaders)


def result_facility_label(station: dict[str, Any]) -> str:
    value = str(station.get("facility_type") or "").strip()
    return "분류 확인 필요" if value in ("", "시설 유형 확인 필요") else value


def reset_result_page() -> None:
    st.session_state.result_page = 0


def clear_facility_selection() -> None:
    st.session_state.facility_groups = list(FACILITY_GROUPS)
    st.session_state.result_facility = "전체"
    reset_result_page()


def render_search() -> None:
    if st.session_state.pop("reset_search_filters", False):
        for key, value in {
            "facility_groups": list(FACILITY_GROUPS), "outsider_filter": "전체", "parking_filter": "전체",
            "result_facility": "전체", "charging_speed": "전체", "place_query": "",
            "suggestion_query": "", "place_suggestions": [], "selected_place": None,
        }.items():
            st.session_state[key] = value
    render_header()
    quality_notices = [str(item) for item in st.session_state.get("quality_notices", []) if item]
    with st.container(key="map_workspace"):
        left, right = st.columns([1, 2.3], gap="medium")
        with left:
            with st.container(border=True, key="search_controls"):
                render_direct_search()
            request = st.session_state.request
            if st.session_state.notice:
                st.warning(st.session_state.notice)
            facility_choice = st.session_state.get("facility_groups", [])
            visible_results = filter_exploration_results(
                st.session_state.results, facility_choice,
                st.session_state.get("outsider_filter", "전체"),
                st.session_state.get("parking_filter", "전체"),
            )
            missing_facilities = sum(result_facility_label(item) == "분류 확인 필요"
                                     for item in st.session_state.results)
            if request and facility_choice and missing_facilities:
                st.caption(f"시설 분류 미확인 {missing_facilities:,}곳은 선택한 분류에서 제외됩니다.")
                if not visible_results:
                    st.button("분류 조건 해제", key="clear_facilities", on_click=clear_facility_selection)
            if request is not None:
                with st.container(key="result_list"):
                    count_slot, filter_slot = st.columns([1, 1.2], vertical_alignment="center",
                                                          gap="small")
                    with filter_slot:
                        options = ["전체"] + list(FACILITY_GROUPS) + ["분류 확인 필요"]
                        if st.session_state.get("result_facility") not in options:
                            st.session_state.result_facility = "전체"
                        selection = st.selectbox("결과 내 분류", options, key="result_facility",
                                                 on_change=reset_result_page)
                    if selection != "전체":
                        if selection == "분류 확인 필요":
                            visible_results = [item for item in visible_results if not any(
                                any(word in str(item.get("facility_type") or "") for word in words)
                                for words in FACILITY_GROUPS.values())]
                        else:
                            visible_results = [item for item in visible_results if any(
                                word in str(item.get("facility_type") or "") for word in FACILITY_GROUPS[selection])]
                    with count_slot:
                        st.markdown(f'<div class="cp-result-title">주변 충전소 <b>{len(visible_results):,}곳</b></div>',
                                    unsafe_allow_html=True)
                    render_station_cards(visible_results)
            else:
                st.markdown('<div class="cp-result-empty">장소를 검색하면<br>주변 충전소가 여기에 표시돼요.</div>',
                            unsafe_allow_html=True)
        with right:
            with st.container(key="map_view"):
                st.iframe(build_map_html(visible_results, request,
                                        st.session_state.get("selected_station_id"), availability_label,
                                        quality_notices=quality_notices),
                          height=735, alt="카카오 지도 기반 충전소 위치와 충전 상태")
    render_chat()


def main() -> None:
    if st.session_state.get("_purge_on_logout"):
        st.session_state.clear()
    init_state()
    st.markdown(STYLES + REDESIGN_STYLES, unsafe_allow_html=True)
    install_capture_notice(bool(access_token()) and st.session_state.role in ("손님", "일반 이용자"))
    if not access_token():
        render_login()
        return
    if st.session_state.view == "dashboard" and can_view_dashboard(st.session_state.role):
        render_dashboard()
    else:
        render_search()


if __name__ == "__main__":
    main()
