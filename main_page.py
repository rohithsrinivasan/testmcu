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

    st.write("Upload pin table in csv format")    
    uploaded_file = st.file_uploader("Upload a CSV  file", type=["csv"])

    if uploaded_file is not None:
        input_csv_file_name = uploaded_file.name
        try:
            #df = pd.read_excel(uploaded_file)
            df = pd.read_csv(uploaded_file)
            print(f"Uploaded file step 2")
        except Exception as e:
            print(f"Error reading excel file: {e}")
            st.error("An error occurred while processing the uploaded file.")
        required_columns = ["Pin Designator", "Pin Display Name", "Electrical Type", "Pin Alternate Name"]
        df = df[required_columns]
        print(f"my df : {df}")
        st.session_state['pin_table'] = df.to_dict('records')
        st.write("Pin table uploaded successfully.")
        st.session_state['pin_table'] = df

if input_buffer:
    if input_part_number:
        with st.spinner('Processing...'):
            time.sleep(5)
            part_number, number_of_pins, package_type, package_code = f.part_number_details(input_part_number, input_buffer)
            pin_table = f.extracting_pin_tables(input_buffer, part_number, number_of_pins, package_type, package_code)
        #st.success("Extraction Done!")
        st.session_state['pin_table'] = pin_table
    else:
        st.warning("Please enter a valid Part Number.")
else:
    st.info("Please upload Input") 

if 'pin_table' in st.session_state:
    pin_table = st.session_state['pin_table']
    before_grouping_flag, added_empty_grouping_column = grouping_functions.check_excel_format(pin_table)
    grouping_done = False

    grouping_strategy = st.session_state.customization.get("grouping_strategy", "Algorithm")      

    if grouping_strategy == "Algorithm":
        pin_grouping_table = grouping_functions.assigning_grouping_as_per_algorithm(added_empty_grouping_column)
        #st.text("After Grouping from Algorithm:")
    
    elif grouping_strategy == "AI":
        json_file = "Database.json"
        pin_grouping_table = grouping_functions.assigning_grouping_as_per_database(added_empty_grouping_column, json_file)
        st.text("After Grouping from Database:")
    
    elif grouping_strategy == "Database":
        st.text("Executing LLM")
        response, pin_grouping_table = grouping_functions.assigning_grouping_as_per_LLM(added_empty_grouping_column)
        st.text("Step 1-")
        st.markdown(f'Type of device :red[{response.text}]')

    else:
        st.write("No grouping strategy selected. Default is Algorithm.")        

    # Common operations after grouping
    #st.dataframe(pin_grouping_table)
    no_grouping_assigned = grouping_functions.check_empty_groupings(pin_grouping_table)
    
    if no_grouping_assigned.empty:
        #st.info("All grouping values are filled.") 
        #st.success("Grouping Done!")
        st.session_state['grouped_pin_table'] = pin_grouping_table          

    else:
        st.info("Please fill in group values for these:")
        edited_df = st.data_editor(no_grouping_assigned)

        if edited_df['Grouping'].isnull().any():
            st.info("Please enter group names for all.")
        else:
            pin_grouping_table.update(edited_df)
            #st.text("Final Grouping Table")
            #st.dataframe(pin_grouping_table)
            #st.success("Grouping Done!")
            st.session_state['grouped_pin_table'] = pin_grouping_table 
                  

if 'grouped_pin_table' in st.session_state:
    grouped_pin_table = st.session_state['grouped_pin_table']

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority']
    additional_column = 'Priority'
    before_priority_flag, added_empty_priority_column = SideAllocation_functions.check_excel_format(grouped_pin_table,required_columns, additional_column)

    priority_added = SideAllocation_functions.assigning_priority_for_group(added_empty_priority_column)

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