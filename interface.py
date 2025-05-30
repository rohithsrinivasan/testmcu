from os import read
import streamlit as st
import pandas as pd
from tabula import read_pdf
import functions as f
import time
import google.generativeai as genai
import json
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

st.set_page_config(page_icon= 'dados/logo_small.png', page_title= "SymbolGen" )

st.page_link("interface.py", label="Extraction")
st.page_link("pages/01_Grouping_2.py", label="Grouping 2.0")
st.page_link("pages/02_Side_Allocation.py", label="SideAlloc")
st.page_link("pages/03_Parameters.py", label="Parameters")

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

# Toggle for Gemini API
use_ai_extrcation = st.toggle("Use Gemini API for extraction")
# Part number input
if "part_number" not in st.session_state:
    st.session_state.part_number = None

input_part_number = st.text_input("Enter a valid Part Number", value=st.session_state.part_number or "")

if st.session_state.input_buffer:
    if not use_ai_extrcation:
        if input_part_number:
            with st.spinner('Processing...'):
                time.sleep(5)
                part_number, number_of_pins, package_type, package_code = f.part_number_details(
                    input_part_number, st.session_state.input_buffer
                )
                st.session_state["part number"] = part_number
                pin_table = f.extracting_pin_tables(
                    st.session_state.input_buffer, part_number, number_of_pins, package_type, package_code
                )
                st.success("Done!")

            # Store values in session state
            st.session_state.part_number = part_number
            st.session_state.pin_table = pin_table

            if "page" in st.session_state and st.session_state["page"] == "grouping":
                st.page_link("pages/01_Grouping_2.py", label="Grouping 2.0")
            else:
                st.write("Pin table displayed")
        else:
            st.warning("Please enter a valid Part Number.")

    elif use_ai_extrcation:
        st.text("Working on AI extraction...")
        with st.spinner('Processing with Gemini API...'):

            try:
                # Craft the prompt for Gemini
                prompt = f'''
                You are an electrical design engineer. Here is a datasheet of a MCU having different sections such as overview, electrical characteristics and ECAD information. You have to focus on the ECAD Information section and takes out the details   
                 1. Pin configuration - It will be having the list if pins based on the part numbers, take the pin number and name based on the part number and structure it to json
                 2. Give me a Json file with key as Part Number and Value as The Table with all 4 columns  

            Json template, please do it Pin Number wise
            "ISL71148SLH": [
                {
                "Pin Number": "",
                "Primary Pin Name": "",
                "Primary Electrical Type " :"",
                    "Alternate Pin Name(s)": ""
                }

                '''

                # Call Gemini API with structured response configuration
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=
                        {
                            "type": "OBJECT",
                            "properties": {
                                "part_number": {"type": "STRING"},
                                "number_of_pins": {"type": "INTEGER"},
                                "package_type": {"type": "STRING"},
                                "package_code": {"type": "STRING"},
                                "pin_table": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "Pin Number": {"type": "STRING"},
                                            "Primary Pin Name": {"type": "STRING"},
                                            "Primary Electrical Type": {"type": "STRING"},
                                            "Alternate Pin Name(s)": {"type": "STRING"}
                                        },
                                        "required": [
                                            "Pin Number",
                                            "Primary Pin Name",
                                            "Primary Electrical Type",
                                            "Alternate Pin Name(s)"
                                        ]
                                    }
                                }
                            },
                            "required": [
                                "part_number",
                                "number_of_pins",
                                "package_type",
                                "package_code",
                                "pin_table"
                            ]
                        }
                    )
                )    

                st.success("AI Extraction Done!")

            except Exception as e:
                st.error(f"Error during AI extraction: {e}")
                st.warning("Please ensure your Gemini API key is valid and the model is accessible.")

            # Download JSON button
            if st.session_state.extracted_json_data:
                json_string = json.dumps(st.session_state.extracted_json_data, indent=4)
                st.download_button(
                    label="Download Extracted Data as JSON",
                    data=json_string,
                    file_name=f"{input_part_number}_details.json" if input_part_number else "extracted_details.json",
                    mime="application/json",
                )

            # Conditional navigation/display
            if "page" in st.session_state and st.session_state["page"] == "grouping":
                st.page_link("pages/01_Grouping_2.py", label="Grouping 2.0")
            else:
                st.write("Pin table displayed")

else:
    st.info("Please upload a PDF file.")



    
    
