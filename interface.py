from os import read
import streamlit as st
import pandas as pd
from tabula import read_pdf
import functions as f
import time

st.set_page_config(page_icon= 'dados/logo_small.png', page_title= "SymbolGen" )

st.page_link("interface.py", label="Extraction")
st.page_link("pages/grouping_2.py", label="Grouping 2.0")
st.page_link("pages/side_allocation.py", label="SideAlloc")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
#st.markdown(hide_st_style, unsafe_allow_html=True)

f.renesas_logo()
f.header_intro() 
f.header_intro_2()

# File uploader
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = None

input_buffer = st.file_uploader("Upload a file", type=("PDF"))

if input_buffer:
    st.session_state.input_buffer = input_buffer  # Store in session state

# Optionally, add a clear button to reset session state
if st.button("Clear Inputs"):
    st.session_state.input_buffer = None
    st.session_state.part_number = None
    st.session_state.pin_table = None
    st.rerun()

# Part number input
if "part_number" not in st.session_state:
    st.session_state.part_number = None

input_part_number = st.text_input("Enter a valid Part Number", value=st.session_state.part_number or "")

if st.session_state.input_buffer:
    if input_part_number:
        with st.spinner('Processing...'):
            time.sleep(5)
            part_number, number_of_pins, package_type, package_code = f.part_number_details(
                input_part_number, st.session_state.input_buffer
            )
            pin_table = f.extracting_pin_tables(
                st.session_state.input_buffer, part_number, number_of_pins, package_type, package_code
            )
            st.success("Done!")

        # Store values in session state
        st.session_state.part_number = part_number
        st.session_state.pin_table = pin_table

        if "page" in st.session_state and st.session_state["page"] == "grouping":
            st.page_link("pages/grouping_2.py", label="Grouping 2.0")
        else:
            st.write("Pin table displayed")

    else:
        st.warning("Please enter a valid Part Number.")
else:
    st.info("Please upload a PDF file.")



    
    
