import streamlit as st
import random



m = st.markdown("""
<style>
div.stButton > button:first-child {
    background-color: #ce1126;
    color: white;
    height: 3em;
    width: 12em;
    border-radius:10px;
    border:3px solid #000000;
    font-size:20px;
    font-weight: bold;
    margin: auto;
    display: block;
}

div.stButton > button:hover {
	background:linear-gradient(to bottom, #ce1126 5%, #ff5a5a 100%);
	background-color:#ce1126;
}

div.stButton > button:active {
	position:relative;
	top:3px;
}

</style>""", unsafe_allow_html=True)

b = st.button("Button 1")

'''
    etalon_lock.toggle("a", key="etalon_lock", value=etalon_lock_status(), label_visibility="collapsed")   
    if etalon_lock:
        control_loop.lock_etalon()
        etalon_state.metric("a", value="🔐", label_visibility="collapsed")
    if not etalon_lock:
        control_loop.unlock_etalon()
        etalon_state.metric("a", value="🔓", label_visibility="collapsed")
    '''