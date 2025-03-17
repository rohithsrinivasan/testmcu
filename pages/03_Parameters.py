import streamlit as st
from tabula import read_pdf
from dotenv import load_dotenv
import functions as f



st.set_page_config(page_icon= 'dados/logo_small.png', page_title= "Parameters" )

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

st.subheader("Parameter Extraction Page")

# Check if session state contains required data
# Check if the keys exist in session state and their values are not None
if "input_buffer" in st.session_state and "part_number" in st.session_state:
    input_buffer = st.session_state.input_buffer
    part_number = st.session_state.part_number

    # Ensure input_buffer is not None before accessing its attributes
    if input_buffer is not None and part_number is not None:
        st.write("File uploaded:", input_buffer.name)
        st.write("Part number entered:", part_number)

        # Call the function to extract the parameter table
        parameter_table = f.parameter_table_extraction_2(input_buffer)

        # Display the extracted data
        #st.subheader("Extracted_parameter data")
        #st.dataframe(parameter_table)
        transposed_table = parameter_table.T

        if len(transposed_table.columns) == 1:
            # If there are exactly 2 columns, rename them directly
            transposed_table = transposed_table.rename(columns={
                0: "Value"
            })
        else:
            new_column_names = {i: f"Column {i+1}" for i in range(len(transposed_table.columns))}
            transposed_table = transposed_table.rename(columns=new_column_names)

            # Look for the column that contains the part_number
            part_number_column = None
            for col in transposed_table.columns:
                if transposed_table[col].astype(str).str.contains(str(part_number)).any():
                    part_number_column = col
                    break

            # If part_number column is found
            if part_number_column is not None:
                st.write("Part number column found:", part_number_column)
                # Keep only the part_number column and drop all others
                transposed_table = transposed_table[[part_number_column]]
                
            else:
                st.write("Part number column not found. Keeping all columns.")

              
        st.subheader("Extracted Parameter Data")                
        st.dataframe(transposed_table)

        st.success("Symbol Parameter Extraction is Complete!!")
    else:
        st.warning("Invalid data in session state. Please upload a file and enter a part number on the main page.")
else:
    st.warning("No data found in session state. Please upload a file and enter a part number on the main page.")