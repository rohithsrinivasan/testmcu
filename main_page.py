from os import read
import streamlit as st
import pandas as pd
from tabula import read_pdf
import functions as f
import grouping_functions
import SideAllocation_functions
import partitioning_functions
import time
import datetime
import os
import streamlit as st
import pandas as pd
from tabula import read_pdf
import grouping_functions
from dotenv import load_dotenv
import google.generativeai as genai
import functions as f
import glob
import ai_functions

st.set_page_config(page_icon= 'dados/logo_small.png', page_title= "SymbolGen" )

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

#st.warning(f"Bad requested resource. Try refreshing")

#f.renesas_logo()
f.header_intro() 
f.header_intro_2()

#st.subheader('Upload your PDF by clicking on "Browse Files"')
input_buffer = st.file_uploader("Upload a file", type=("PDF"))
input_part_number = st.text_input("Enter a valid Part Number")
input_loaded = False

@st.dialog("Customize")
def customise():
    device_category = st.selectbox("Please Select Device Category", ["MCU/MPU", "Power", "Clock & Timing","Analog","Interface","Wireless & Connectivity"])
    grouping_strategy = st.selectbox("Please select Strategy for grouping", ["Algorithm", "LLM Model", "Database"])
    layout_style = st.selectbox("Please select Layout style", ["DIL", "Connector", "Quad"])

    if st.button("Submit"):
        st.session_state.customization = {
            "device_category": device_category,
            "grouping_strategy": grouping_strategy,
            "layout_style": layout_style
        }
        st.rerun()

if "customization" not in st.session_state:
    st.session_state.customization = {
        "device_category": "MCU",
        "grouping_strategy": "Algorithm",
        "layout_style": "DIL"
    }
         

#st.write("Click on Customize to set your preferences")
if st.button("Customize ⚙️"):
    customise()

non_standard = st.toggle("For Non Standard Datasheet")

if non_standard:

    st.write("Upload pin table in table format")    
    uploaded_csv = st.file_uploader("Upload a exel  file", type=["csv","xlsx"])

    if uploaded_csv is not None:
        try:
            # Try reading the uploaded file
            input_csv_file_name = uploaded_csv.name
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
        st.session_state["part number"] = df.loc[0, 'comment'] if 'comment' in df.columns else None

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

        required_columns = ["Pin Designator", "Pin Display Name", "Electrical Type", "Pin Alternate Name"]
        df = df[[col for col in required_columns if col in df.columns]]


        # Filter out rows where "Pin Alternate Name" contains "renesas"
        if "Pin Alternate Name" in df.columns:
            df = df[~df["Pin Alternate Name"].str.contains("renesas", case=False, na=False)]
            df = df[~df["Pin Alternate Name"].str.contains("Cortex", case=False, na=False)]

        # Always render the toggle switch
        # testing_electrical_type = st.toggle("Testing Electrical Type", value=False)

        # # If toggle is enabled and "Electrical Type" column exists, remove it
        # if testing_electrical_type and "Electrical Type" in df.columns:
        #     df = df.drop(columns=["Electrical Type"])
        #     st.write("'Electrical Type' column has been removed.")
        # elif "Electrical Type" not in df.columns:
        #     st.write("'Electrical Type' column is not present in the DataFrame.")
        # else:
        #     st.write("'Electrical Type' column is retained.")



        # Display warnings if any adjustments were made
        if warnings:
            for warning in warnings:
                st.warning(warning)

        # Display cleaned DataFrame
        #st.write("Processed Data:")
        #st.dataframe(df)
        st.session_state['pin_table'] = df.to_dict('records')
        st.write("Pin table uploaded successfully.")
        st.session_state['pin_table'] = df

    else:
        st.warning("Please upload an Excel file to continue")


if input_buffer:
    if input_part_number:
        with st.spinner('Processing...'):
            time.sleep(5)
            part_number, number_of_pins, package_type, package_code = f.part_number_details(input_part_number, input_buffer)
            st.session_state['part number'] = part_number
            pin_table = f.extracting_pin_tables(input_buffer, part_number, number_of_pins, package_type, package_code)
        #st.success("Extraction Done!")
        st.session_state['pin_table'] = pin_table
    else:
        st.warning("Please enter a valid Part Number.")
else:
    print("Please upload Input") 

if 'pin_table' in st.session_state:
    pin_table = st.session_state['pin_table']

    col1, col2 = st.columns(2)

    # Button 1: Clear Pin Table (Light Blue)
    with col1:
        if st.button("Clear Pin Table", type="secondary"):
            del st.session_state['pin_table']
            st.write("Pin table cleared.")
            st.rerun()

    # Button 2: Remove Electrical Type (Darker Blue)        
    with col2:
        if st.button("Remove Electrical Type", type="secondary"):
            pin_table_without_type, electrical_type_removed = grouping_functions.remove_electrical_type(pin_table)
            st.session_state['pin_table'] = pin_table_without_type 
            st.session_state['electrical_type_removed'] = electrical_type_removed 

    st.write (f"Part Number : **{st.session_state["part number"]}**")
    st.write("Pin Table:")
    st.dataframe(st.session_state['pin_table'])
    #st.text(f"Before Pin Grouping Flag :{before_grouping_flag}")
    #st.dataframe(added_empty_grouping_column)
    #mcu = st.checkbox("Use Algorithm (MCU) for grouping")
    #database = st.checkbox("Use database for grouping")
    #llm_model = st.checkbox("Use hugging face model (trained)")

    electrical_type_removed = "Electrical Type" not in st.session_state['pin_table'].columns
    database_for_pin_type = False
    database_for_grouping = False

    if electrical_type_removed:
        # Show this checkbox if "Electrical Type" is removed
        database_for_pin_type = st.checkbox("Use database for pin type")
    else:
        # Show this checkbox if "Electrical Type" is present
        database_for_grouping = st.checkbox("Use database for grouping")

    #if not any([database, llm_model]):
    #    st.info("Make a selection")
    #    pin_grouping_table = pd.DataFrame()

    #elif sum([database, llm_model]) > 1:
    #    st.info("Please only make a single selection")
    #    pin_grouping_table = pd.DataFrame()

    json_paths = {
        'Input': 'mcu_database/mcu_input.json',
        'Power': 'mcu_database/mcu_power.json',
        'Output': 'mcu_database/mcu_output.json',
        'I/O': 'mcu_database/mcu_io.json',
        'Passive': 'mcu_database/mcu_passive.json'
    }

    if database_for_pin_type:
        st.warning("This feature is not fully developed.")
        pin_table = st.session_state['pin_table']
        before_pin_type_flag, added_empty_pin_type_column = grouping_functions.check_excel_format_for_type(pin_table)
        pin_type_added_table = grouping_functions.assigning_pin_type_as_per_database(added_empty_pin_type_column, json_paths) 
        st.dataframe(pin_type_added_table)
        st.session_state['pin_table'] = pin_type_added_table
        database_for_grouping = st.checkbox("Use database for grouping")
        
    if database_for_grouping:
        st.success("Using database for grouping")
        pin_table = st.session_state['pin_table']
        before_grouping_flag, added_empty_grouping_column = grouping_functions.check_excel_format_for_grouping(pin_table)
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
            #st.success("Done!")
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
        st.info("Please the checkbox for using database")
        pin_grouping_table = pd.DataFrame()                            


    # Check if redirection to "SideAlloc" page is needed
    #if "page" in st.session_state and st.session_state["page"] == "SideAlloc":
        #st.page_link("pages/02_Side_Allocation.py", label="SideAlloc")
    #else:
        #print("Grouped Pin table displayed") 
        #st.write("Grouped Pin table displayed")
                  

if 'grouped_pin_table' in st.session_state:
    grouped_pin_table = st.session_state['grouped_pin_table']

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority']
    additional_column = 'Priority'
    before_priority_flag, added_empty_priority_column = SideAllocation_functions.check_excel_format(grouped_pin_table,required_columns, additional_column)

    priority_mapping_json = f"priority_mappings_2.json"
    priority_added = SideAllocation_functions.assigning_priority_for_group(added_empty_priority_column,priority_mapping_json)

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority', 'Side']
    additional_column = 'Side'
    before_side_flag, added_empty_side_column = SideAllocation_functions.check_excel_format(priority_added,required_columns, additional_column)

    if len(added_empty_side_column) < 80:
        side_added = SideAllocation_functions.assigning_side_for_priority(added_empty_side_column)

    else:
        st.text(f"Executing Partioning")
        df_dict = partitioning_functions.partitioning(added_empty_side_column)
        #st.text("Raw data dict")
        #for subheader, dataframe in df_dict.items():
        #    st.subheader(subheader)
        #    st.dataframe(dataframe)
        side_added_dict = partitioning_functions.assigning_side_for_priority_for_dataframes_within_dictionary(df_dict)
        st.text(f"Side Column Added")
        #for subheader, dataframe in side_added_dict.items():
        #    st.subheader(subheader)
        #    st.dataframe(dataframe)

        side_added = side_added_dict

    layout_style = st.session_state.customization.get("layout_style", "DIL")  
    if layout_style:

        required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority', 'Side', 'Changed Grouping']
        additional_column = 'Changed Grouping'
        before_new_grouping_flag, added_empty_new_grouping_column = SideAllocation_functions.check_excel_format(side_added,required_columns, additional_column)        


        grouping_changed = SideAllocation_functions.Dual_in_line_as_per_Renesas(added_empty_new_grouping_column)
        #st.text(f"DIL template as per Renesas")

        required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Side', 'Changed Grouping','Description']
        additional_column = 'Description'
        before_description_flag, added_empty_description_column = SideAllocation_functions.check_excel_format(grouping_changed ,required_columns, additional_column) 

        gemini_api_key = "AIzaSyDQtcnAOBKCHdXo48OSaPXNTS2JaHo2FyM"
        #description_added = ai_functions.Add_Description_for_pin(added_empty_description_column,gemini_api_key)

        with st.status("🔄 Processing pin descriptions", expanded=True) as status:
            
            # 2. Add a visual spinner
            with st.spinner("Generating AI-powered descriptions..."):
                
                # 3. Your time-consuming function
                try:
                    description_added = ai_functions.Add_Description_for_pin(
                        added_empty_description_column,
                        gemini_api_key
                    )
                    
                    # 4. Success message
                    status.update(label="✅ Descriptions completed!", state="complete")
                    grouping_changed = description_added
                    
                except Exception as e:
                    # 5. Error handling
                    status.update(label="❌ Failed to generate descriptions", state="error")
                    st.error(f"Error: {str(e)}")
                    st.stop()
                    grouping_changed= grouping_changed

        if isinstance(grouping_changed, pd.DataFrame):
            grouping_changed = SideAllocation_functions.final_filter(grouping_changed) 
            st.subheader(f"Smart_Table: ")
            st.dataframe(grouping_changed)  # Display single DataFrame
            #st.success("Side Alloction Done!")

            timestamp = datetime.datetime.now().strftime("%d-%m_%H:%M")
            try:
                filename = f"{part_number}_SmartPinTable_{timestamp}.csv"
            except NameError:
                try:
                    filename = f"{input_csv_file_name}_SmartPinTable_{timestamp}.csv"
                except NameError:
                    print("Error: File name could not be generated. Please check the variables 'part_number' and 'input_csv_file_name'.")
                    filename = "None"           

            st.download_button(
                label="Download Smart Table",
                data=grouping_changed.to_csv(index=False),
                file_name=filename,
                mime='text/csv',
                type="primary"
            )

        # Assuming `grouping_changed` is a dictionary of DataFrames
        elif isinstance(grouping_changed, dict):
            for key, df in grouping_changed.items():
           # for key, df in {k: v for k, v in grouping_changed.items() if not v.empty}.items(): 
                df = SideAllocation_functions.final_filter(df)   
                st.subheader(f"Smart_Table: {key}")  # Display the key as a subheader
                st.dataframe(df)

            # Prepare the filename
            timestamp = datetime.datetime.now().strftime("%d-%m_%H:%M")
            filename = f"{part_number}_SmartPinTable_{timestamp}.xlsx"

            # Save to an Excel file with multiple sheets using 'openpyxl'
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                for sheet_name, df in grouping_changed.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Read the Excel file as binary to enable download
            with open(filename, 'rb') as f:
                excel_data = f.read()

            # Provide download button for the Excel file
            st.download_button(
                label="Download All",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )


        else:   
            st.text(f"Error Occured in Displaying Dataframes")               


else:
    print("No Grouped Pin table available.")
    #st.write("No Grouped Pin table available.")          