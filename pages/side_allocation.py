import os
import streamlit as st
import pandas as pd
from tabula import read_pdf
import SideAllocation_functions
from dotenv import load_dotenv
import google.generativeai as genai
import functions as f

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

st.subheader("Side Allocation Page")

if 'grouped_pin_table' in st.session_state:
    grouped_pin_table = st.session_state['grouped_pin_table']

    #st.write("Grouped Pin Table:")
    #st.dataframe(grouped_pin_table)

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority']
    additional_column = 'Priority'
    before_priority_flag, added_empty_priority_column = SideAllocation_functions.check_excel_format(grouped_pin_table,required_columns, additional_column)
    #st.text(f"Before Side Allocation Flag :{before_priority_flag}")
    #st.dataframe(added_empty_priority_column)
    priority_added = SideAllocation_functions.assigning_priority_for_group(added_empty_priority_column)
    #st.text(f"Priority Column Added")
    #st.dataframe(priority_added)

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority', 'Side']
    additional_column = 'Side'
    before_side_flag, added_empty_side_column = SideAllocation_functions.check_excel_format(priority_added,required_columns, additional_column)
    #st.text(f"Before Side Allocation Flag :{before_side_flag}")
    #st.dataframe(added_empty_side_column)

    if len(added_empty_side_column) < 80:
        side_added = SideAllocation_functions.assigning_side_for_priority(added_empty_side_column)
        #st.text(f"Side Column Added")
        #st.dataframe(side_added)

    else:
        st.text(f"Executing Partioning")
        df_dict = SideAllocation_functions.partitioning(added_empty_side_column)
        #st.text("Raw data dict")
        #for subheader, dataframe in df_dict.items():
        #    st.subheader(subheader)
        #    st.dataframe(dataframe)
        side_added_dict = SideAllocation_functions.assigning_side_for_priority_for_dataframes_within_dictionary(df_dict)
        #st.text(f"Side Column Added")
        #for subheader, dataframe in side_added_dict.items():
        #    st.subheader(subheader)
        #    st.dataframe(dataframe)


        #side_added = SideAllocation_functions.convert_dict_to_list(df_dict)
        side_added = side_added_dict

    #st.text("Choose Layout Style")
    #changing_as_per_style_guide = st.checkbox("Layout Style : DIL")

    if side_added is not None:
    #if changing_as_per_style_guide:

        required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping','Priority', 'Side', 'Changed Grouping']
        additional_column = 'Changed Grouping'
        before_new_grouping_flag, added_empty_new_grouping_column = SideAllocation_functions.check_excel_format(side_added,required_columns, additional_column)        


        grouping_changed = SideAllocation_functions.Dual_in_line_as_per_Renesas(added_empty_new_grouping_column)
        #st.text(f"DIL template as per Renesas")

        if isinstance(grouping_changed, pd.DataFrame):
            st.dataframe(grouping_changed)  # Display single DataFrame
        elif isinstance(grouping_changed, dict):
            for key, df in grouping_changed.items():
                st.subheader(f"DataFrame: {key}")  # Display the key as a subheader
                st.dataframe(df) 


else:
    st.write("No Grouped Pin table available.")  
