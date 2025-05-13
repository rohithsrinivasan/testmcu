import streamlit as st
import pandas as pd
from tabula import read_pdf
import functions as f
import Side_Allocation_function_new as SideAllocation_functions
import datetime


st.set_page_config(page_icon= 'dados/logo_small.png', page_title= "SymbolGen" )

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
#st.markdown(hide_st_style, unsafe_allow_html=True)

if "part number" in st.session_state:
    part_number = st.session_state["part number"]
if "uploaded_csv_name" in st.session_state:
    input_csv_file_name = st.session_state["uploaded_csv_name"]


f.header_intro()
f.header_intro_2()

st.subheader("Side Allocation Page")
if 'grouped_pin_table' in st.session_state:
    grouped_pin_table = st.session_state['grouped_pin_table']

    st.write("Grouped Pin Table:")
    st.dataframe(grouped_pin_table)


    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority']
    additional_column = 'Priority'
    before_priority_flag, added_empty_priority_column = SideAllocation_functions.check_excel_format(grouped_pin_table,required_columns, additional_column)
    #st.text(f"Before Side Allocation Flag :{before_priority_flag}")
    #st.dataframe(added_empty_priority_column)
    priority_mapping_json = f"priority_mappings_2.json"
    priority_added = SideAllocation_functions.assigning_priority_for_group(added_empty_priority_column,priority_mapping_json)
    #st.text(f"Priority Column Added")
    #st.dataframe(priority_added)

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority', 'Side']
    additional_column = 'Side'
    before_side_flag, added_empty_side_column = SideAllocation_functions.check_excel_format(priority_added,required_columns, additional_column)

    if len(added_empty_side_column) <= 80:
        side_added = SideAllocation_functions.assigning_side_for_priority(added_empty_side_column)
        st.text(f"Side Column Added")
        st.dataframe(side_added)
    
    else:
        st.text(f"Executing Partioning")
        df_dict = SideAllocation_functions.partitioning(added_empty_side_column)
        side_added_dict = SideAllocation_functions.assigning_side_for_priority_for_dataframes_within_dictionary(df_dict)
        st.text(f"Side Column Added")
        for subheader, dataframe in side_added_dict.items():
            st.subheader(subheader)
            st.dataframe(dataframe)


        #side_added = SideAllocation_functions.convert_dict_to_list(df_dict)
        side_added = side_added_dict

    if isinstance(side_added, pd.DataFrame):
        side_added = SideAllocation_functions.final_filter(side_added) 
        st.subheader(f"Smart_Table: ")
        st.dataframe(side_added)  # Display single DataFrame
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
            data=side_added.to_csv(index=False),
            file_name=filename,
            mime='text/csv',
            type="primary"
        )

    # Assuming `side_added` is a dictionary of DataFrames
    elif isinstance(side_added, dict):

        side_added = {k: v for k, v in side_added.items() if not v.empty}

        for key in side_added:
            df = SideAllocation_functions.final_filter(df)   
            st.markdown(f"<h5>Smart Table: {key}</h5>", unsafe_allow_html=True)
            st.dataframe(df)

        # Prepare the filename
        timestamp = datetime.datetime.now().strftime("%d-%m_%H:%M")
        try:
            filename = f"{part_number}_SmartPinTable_{timestamp}.xlsx"
        except NameError:
            try:
                filename = f"{input_csv_file_name}_SmartPinTable_{timestamp}.xlsx"
            except NameError:
                st.error("Error: File name could not be generated. Please check the variables 'part_number' and 'input_csv_file_name'.")
                filename = None

        if filename:
            # Save to an Excel file with multiple sheets using 'openpyxl'
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                for sheet_name, df in side_added.items():
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
