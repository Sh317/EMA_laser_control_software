import streamlit as st

st.title("My Awesome App")

@st.experimental_fragment()
def toggle_and_text():
    cols = st.columns(2)
    t = cols[0].toggle("Toggle")
    w = cols[1].text_area("Enter text")
    st.markdown(w)

@st.experimental_fragment()
def filter_and_file():
    cols = st.columns(2)
    cols[0].checkbox("Filter")
    cols[1].file_uploader("Upload image")

toggle_and_text()
cols = st.columns(2)
cols[0].selectbox("Select", [1,2,3], None)
cols[1].button("Update")
filter_and_file()

@st.experimental_fragment()
def scan_settings():
    c1, c2 = st.columns(2, vertical_alignment='bottom')
    start_wnum = c1.number_input("Start Wavenumber (cm^-1)", 
                                value=1.,
                                step=0.00001, 
                                format="%0.5f"
                                )
    end_wnum = c2.number_input("End Wavenumber (cm^-1)", 
                                value=2.,
                                step=0.00001, 
                                format="%0.5f"
                                )
    no_of_steps = c1.number_input("No. of Steps", 
                                value=5,
                                max_value=500
                                )
    time_per_scan = c2.number_input("Time per scan (sec)", 
                                    value=2.0,
                                    step=0.1
                                    )
    scan_range = end_wnum - start_wnum
    wnum_per_scan = scan_range / no_of_steps
    wnum_to_freq = 30
    no_of_steps_display, time_per_scan_display = no_of_steps, time_per_scan
    exscander = st.expander("Scan Info")
    st.button("rerun")
    st.write(start_wnum)
    with exscander:
        col1, col2 = st.columns(2)
        conversion_checkbox = col1.checkbox("In Hertz? (Wavenumber in default)")
        col2.markdown(":red[_Please review everything before scanning_]")
        if conversion_checkbox: 
            mode = "Frequency"
            unit = "GHz"
            start_wnum_display, end_wnum_display, scan_range_display= start_wnum * wnum_to_freq, end_wnum * wnum_to_freq, scan_range * wnum_to_freq
        else:
            mode = "Wavenumber"
            unit = "/cm"
            start_wnum_display, end_wnum_display, scan_range_display, no_of_steps_display = start_wnum, end_wnum, scan_range, no_of_steps
        st.markdown(f"Start Point({unit}): {start_wnum_display}   End Point({unit}): {end_wnum_display} \n Total Scan Range({unit}): {scan_range_display}   Number of Steps: {no_of_steps_display} \n Time Per Scan(s): {time_per_scan_display}   {mode} Per Scan({unit}): {wnum_per_scan}")

scan_settings()