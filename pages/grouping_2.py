import os
import streamlit as st
import pandas as pd
from tabula import read_pdf
import grouping_functions
from dotenv import load_dotenv
import google.generativeai as genai
import functions as f
import glob

st.set_page_config(page_icon= 'dados/logo_small.png', page_title= "SymbolGen" )

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
#st.markdown(hide_st_style, unsafe_allow_html=True)

f.header_intro()
f.header_intro_2()

st.subheader("Grouping Page")

if 'pin_table' in st.session_state:
    pin_table = st.session_state['pin_table']

    if st.button("Clear Pin Table"):
        del st.session_state['pin_table']
        st.write("Pin table cleared.")
   

    st.write("Pin Table:")
    st.dataframe(pin_table)
    before_grouping_flag, added_empty_grouping_column = grouping_functions.check_excel_format(pin_table)
    #st.text(f"Before Pin Grouping Flag :{before_grouping_flag}")
    #st.dataframe(added_empty_grouping_column)

    #mcu = st.checkbox("Use Algorithm (MCU) for grouping")
    database = st.checkbox("Use database for grouping")
    #llm_model = st.checkbox("Use hugging face model (trained)")

    #if not any([database, llm_model]):
    #    st.info("Make a selection")
    #    pin_grouping_table = pd.DataFrame()

    #elif sum([database, llm_model]) > 1:
    #    st.info("Please only make a single selection")
    #    pin_grouping_table = pd.DataFrame()
        
    if database:

        json_paths = {
            'input': 'mcu_database/mcu_input.json',
            'power': 'mcu_database/mcu_power.json',
            'output': 'mcu_database/mcu_output.json',
            'io': 'mcu_database/mcu_io.json',
            'passive': 'mcu_database/mcu_passive.json'
        }

        pin_grouping_table = grouping_functions.assigning_grouping_as_per_database(added_empty_grouping_column, json_paths)  


        #json_file = "Database.json"
        #pin_grouping_table = grouping_functions.assigning_grouping_as_per_database(added_empty_grouping_column, json_file)
        #st.text("After Grouping from Database:")
    
    #elif llm_model:
    #    st.text("Executing LLM")
    #    response, pin_grouping_table = grouping_functions.assigning_grouping_as_per_LLM(added_empty_grouping_column)
    #    st.text("Step 1-")
    #    st.markdown(f'Type of device :red[{response.text}]')

    # Common operations after grouping
        st.dataframe(pin_grouping_table)
        no_grouping_assigned = grouping_functions.check_empty_groupings(pin_grouping_table)
        
        if no_grouping_assigned.empty:
            st.info("All grouping values are filled.") 
            st.success("Done!")
            st.session_state["page"] = "SideAlloc" 
            st.session_state['grouped_pin_table'] = pin_grouping_table            

        else:
            st.info("Please fill in group values for these:")
            edited_df = st.data_editor(no_grouping_assigned)
            edit_database = st.toggle("Edit Database", value=False)

            with st.sidebar:
                st.header("Help Box")
                user_input = st.text_input("Enter Pin Name to get suggestions:")

                json_file_paths = glob.glob(os.path.join('mcu_database', '*.json'))
                json_data = grouping_functions.load_json_files(json_file_paths)

                if user_input:
                    suggestions = grouping_functions.get_suggestions(user_input, json_data)
                    st.write("Suggestions:")
                    for suggestion, score in suggestions:
                        st.write(f"{suggestion} (Match: {score}%)")

            if edit_database:
                json_data_labelled = grouping_functions.load_json_files_with_type_labels('mcu_database')
                for index, row in edited_df.iterrows():
                    pin_name = row['Pin Display Name']
                    group_name = row['Grouping']

                    if group_name:  # If Grouping is filled
                        group_found = False
                        for file_path, data in json_data_labelled.items():
                            if group_name in data:  # Check if group exists in this JSON file
                                if pin_name not in data[group_name]:  # Check if pin already exists
                                    data[group_name].append(pin_name)  # Add pin to the group
                                    grouping_functions.save_json_file(file_path, data)  # Save updated JSON file
                                    st.markdown(
                                        f"<p style='color: green;'>Pin '{pin_name}' has been added to Group '{group_name}' in '{os.path.basename(file_path)}'.</p>",
                                        unsafe_allow_html=True
                                    )
                                    #st.info(f"Pin '{pin_name}' has been added to Group '{group_name}' in '{os.path.basename(file_path)}'.")
                                else:
                                    st.info(f"Pin '{pin_name}' already exists in Group '{group_name}' in '{os.path.basename(file_path)}'.")
                                group_found = True
                                break  # Exit loop once the group is found

                        if not group_found:  # If group is not found in any JSON file
                            st.warning(f"Group '{group_name}' not found in any JSON file. Skipping update for Pin '{pin_name}'.")
            else:
                print("Edit Database is OFF. No updates will be made to JSON files.")
                #st.info("Edit Database is OFF. No updates will be made to JSON files.")



            if edited_df['Grouping'].isnull().any():
                st.info("Please enter group names for all.")

            else:
                pin_grouping_table.update(edited_df)
                st.text("Final Grouping Table")
                st.dataframe(pin_grouping_table)
                st.success("Done!")
                st.session_state["page"] = "SideAlloc" 
                st.session_state['grouped_pin_table'] = pin_grouping_table 

    else:
        st.info("Please select a method for grouping.")
        pin_grouping_table = pd.DataFrame()                            


    # Check if redirection to "SideAlloc" page is needed
    if "page" in st.session_state and st.session_state["page"] == "SideAlloc":
        st.page_link("pages/side_allocation.py", label="SideAlloc")
    else:
        print("Grouped Pin table displayed") 
        #st.write("Grouped Pin table displayed")           

else:
    st.write("No pin table available.")     
    uploaded_csv = st.file_uploader("Upload a exel  file", type=["csv","xlsx"])

    if uploaded_csv is not None:
        try:
            # Try reading the uploaded file
            st.session_state["uploaded_csv_name"] = uploaded_csv.name
            if uploaded_csv.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_csv)
            else:
                df = pd.read_csv(uploaded_csv)

            st.write("File uploaded successfully.")
        
        except Exception as e:
            st.error(f"An error occurred while processing the uploaded file: {e}")
            st.stop()  # Stop execution if file can't be read

        # Convert column names to lowercase for case-insensitive handling
        df.columns = df.columns.str.lower()

        # Define required column mappings
        column_mappings = {
            "designator": "Pin Designator",
            "pin designator": "Pin Designator",
            "name": "Pin Display Name",
            "pin name": "Pin Display Name",
            "electrical": "Electrical Type",
            "electrical type": "Electrical Type",
            "description": "Pin Alternate Name"
        }

        # Find and rename matching columns
        new_column_names = {}
        warnings = []

        for col in df.columns:
            for key, value in column_mappings.items():
                if col.lower() == key.lower():
                    new_column_names[col] = value

        if new_column_names:
            df = df.rename(columns=new_column_names)
            warnings.append("Column names were adjusted due to mismatches.")

        # Keep only required columns
        required_columns = ["Pin Designator", "Pin Display Name", "Electrical Type", "Pin Alternate Name"]
        df = df[[col for col in required_columns if col in df.columns]]

        if "Pin Alternate Name" in df.columns:
            df = df[~df["Pin Alternate Name"].str.contains("renesas", case=False, na=False)]

        # Display warnings if any adjustments were made
        if warnings:
            for warning in warnings:
                st.warning(warning)

        # Display cleaned DataFrame
        st.write("Processed Data:")
        st.dataframe(df)
        st.session_state['pin_table'] = df.to_dict('records')
        st.write("Pin table uploaded successfully.")
        st.session_state['pin_table'] = df
        st.rerun()



