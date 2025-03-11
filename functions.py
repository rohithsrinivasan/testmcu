import streamlit as st
import base64
from io import BytesIO
from tabula import read_pdf
import part_number_details_functions
import extracting_pin_tables_functions
import pdfplumber
import pandas as pd
def renesas_logo():

    image_path = 'dados/logo3.png'
    #st.logo(image_path) 
    print(f"Renesas Logo to be displayed...error")

def header_intro():
    col1, col3 = st.columns([1, 1])

    with col1:
        st.markdown("""
            <h1 style='color: #1c508c; font-size: 39px; vertical-align: top;'>SymbolGen</h1>
            <p style='font-size: 16px;'>Testing version 1.3 - Last update 06/03/2025</p>
        """, unsafe_allow_html=True)

    with col3:
        st.image('dados/logo3.png', width=250)
    
def header_intro_2():
    #st.write("This application's main functionality is to create Schematic Symbols from Standardised Datasheets and generate the .csv downloadable ")   
    st.write("Create schematic symbols from Renesas' new datasheets with ECAD Design information and generate a smart Symbol table. The smart table can be imported into Altium to generate an intelligent symbol.")

def downfile(df):
    towrite = BytesIO()
    downloaded_file = df.to_excel(towrite, index=False, header=True)
    towrite.seek(0)  # reset pointer
    b64 = base64.b64encode(towrite.read()).decode()  # some strings
    linko = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="pdfextractorbylucimartins.xlsx">Download Excel File</a>'
    st.markdown(linko, unsafe_allow_html=True)

def table_processing(input_buffer):
    if input_buffer:
        try:
            input_loaded = read_pdf(input_buffer, pages='all')
            st.write(f' - {len(input_loaded)} tables were found in your PDF.')
            T = True
        except Exception as e:
            st.text("Error {}".format(e))

    if input_loaded:
        list_ = list(range(0,len(input_loaded)))
        In1 = st.selectbox('Select which table you want to view and download:', list_)
        st.dataframe(input_loaded[In1])
        downfile(input_loaded[In1]) 


def part_number_details(input_part_number,input_buffer):
    start_keyword = "part number indexing"
    end_keyword = "symbol pin information"
    part_number_index_pages = part_number_details_functions.find_pages_between_keywords(input_buffer, start_keyword, end_keyword)
    st.text(f'Part Number Indexing pages : {part_number_index_pages}')
    dfs = part_number_details_functions.extracting_tables_in_pages(input_buffer, part_number_index_pages)
    st.text(f"Number of PartNumber indexing table(s): {len(dfs)}")

    Before_merging_flag = part_number_details_functions.before_merging(dfs)
    st.text(f"Before_merging_flag : {Before_merging_flag}")
    if Before_merging_flag:
        merged_df = part_number_details_functions.merge_tables(dfs)
        #st.dataframe(merged_df)
        part_number,number_of_pins,package_type,package_code = part_number_details_functions.search_for_part_number_in_the_indexing_table(merged_df, input_part_number)
        if not all(value is not None for value in (part_number, number_of_pins, package_type, package_code)):
            st.text(f" User entered Part Number is not matching, please select one from the below")
            part_number, number_of_pins, package_type, package_code = part_number_details_functions.create_selectbox_for_user_to_select(merged_df)

        #st.caption(f"Part Number : {part_number}, Number of Pins: {number_of_pins}, Package: {package_type}, Package Code: {package_code}")
        st.caption(f"Part Info : {number_of_pins} - {package_type}")
        #st.divider()

    return part_number, number_of_pins, package_type, package_code  

def extracting_pin_tables(file_path, part_number, number_of_pins, package_type, package_code):
    #pin_string = f"{number_of_pins}-{package_type}"
    start_keyword = "symbol pin information"
    end_keyword = "symbol parameters"
    pin_configuration_pages  = part_number_details_functions.find_pages_between_keywords(file_path, start_keyword, end_keyword)
    #st.text(f'Pin Configuration Pages : {pin_configuration_pages}')
    pin_string = f"{number_of_pins}-"
    package_string = f"{package_type}"
    table_starting_page_number, table_start_string, table_stop_string, table_ending_page_number = extracting_pin_tables_functions.find_table_starting_and_stopping_based_on_pin_string(file_path, pin_configuration_pages, pin_string, package_string)
    st.text(f"Starting Page Number : {table_starting_page_number}, Table Starting Section : {table_start_string}, Table Stopping Section : {table_stop_string} , Ending Page Number : {table_ending_page_number}" )
    pin_table_pages = extracting_pin_tables_functions.generate_list_of_page_numbers(table_starting_page_number, table_ending_page_number)
    # Use these dfs as tables
    st.text(f"Pin Table Pages : {pin_table_pages}")
    dfs = extracting_pin_tables_functions.extracting_pin_tables_in_pages(file_path, pin_table_pages)
    for df in dfs:
        st.dataframe(df)
    # Use these dfs as text
    extracted_table_as_text = extracting_pin_tables_functions.extract_table_as_text(file_path, pin_table_pages, table_start_string,table_stop_string )
    page_numbers = extracting_pin_tables_functions.generate_list_of_page_numbers(table_starting_page_number,table_ending_page_number)
    #st.image(file_path, pages=page_numbers)
    table_as_text = extracting_pin_tables_functions.text_filter(extracted_table_as_text)
    #st.text_area(f" Table as text : \n {table_as_text}")
    # Creating combinatios of tablesas strings
    combo_dict, num = extracting_pin_tables_functions.combine_dataframes_and_print_dictionary(dfs)
    top_3_combinations = extracting_pin_tables_functions.filter_top_3_by_size(combo_dict, table_as_text)
    st.text(top_3_combinations)
    reduced_combo_dict  = extracting_pin_tables_functions.filter_combo_dict_based_on_size_filter(combo_dict, top_3_combinations)
    #st.text(reduced_combo_dict)
    noise_calculation_combo_dict, min_key = extracting_pin_tables_functions.compare_input_string_with_value_string(reduced_combo_dict, table_as_text)
    st.text(f"Mapping After noise filter Algo : {noise_calculation_combo_dict}")
    st.text(min_key)
    final_pin_tables_to_be_merged, number= extracting_pin_tables_functions.get_dataframes_from_tuple(dfs, min_key)
    st.text(f" Number of Selected Dataframes : {number}")
    Before_merging_flag  = part_number_details_functions.before_merging(final_pin_tables_to_be_merged)
    st.text(f"Before Merging Flag : {Before_merging_flag}")
    if Before_merging_flag:
        merged_df = part_number_details_functions.merge_tables(final_pin_tables_to_be_merged)
        st.header(f"\nExtracted Pin Table")
        merged_df = st.data_editor(merged_df) 
        #st.write("Page Preview:")
        #binary_data = file_path.getvalue()
        #pdf_viewer(binary_data, pages_to_render = page_numbers)                      

        #create_navigation_button(merged_df)
        st.session_state["page"] = "grouping"    

    return merged_df


def create_navigation_button(dataframe):
    if dataframe is not None:
        if st.button("Next: Grouping", key="navigation_button"):
            st.session_state["page"] = "grouping"
            st.switch_page("pages/grouping.py")
    else:
        st.button("Next: Grouping (Disabled)", disabled=True, key="navigation_button")


#######################################################################

def parameter_table_extraction_2(input_buffer):

  with pdfplumber.open(input_buffer) as pdf:
    page_numbers = find_page_range(pdf, "Symbol Parameters", "Footprint Design Information")

    if page_numbers:
      st.write(f"Pages containing 'Symbol Parameters' to 'Footprint Design Information': {page_numbers}")
      parameter_tables = extract_tables_in_these_pages(input_buffer, page_numbers)
      st.table(parameter_tables)

      if parameter_tables:
        merged_table = merge_parameter_tables(parameter_tables)
        final_table = remove_rows_with_more_empty_values(merged_table)
        st.table(merged_table)
        return final_table
      else:
        st.write("No tables found in the specified pages.")
    else:
      st.write("Page with 'Symbol Parameters' not found.")

  return None

def find_page_range(pdf_file, start_string, end_string):

  page_numbers = []
  found_start = False

  for page_num, page in enumerate(pdf_file.pages):
    text = page.extract_text()
    if found_start:
      if end_string in text:
        break
      page_numbers.append(page_num + 1)

    if start_string in text:
      found_start = True
      page_numbers.append(page_num + 1)

  return page_numbers if page_numbers else None

def extract_tables_in_these_pages(input_buffer, page_numbers):
  all_tables = []
  with pdfplumber.open(input_buffer) as pdf:
    for page_num in page_numbers:
      try:
        page = pdf.pages[page_num - 1]  # Access by 0-based indexing
        tables = page.extract_tables()
        all_tables.extend(tables)  # Add extracted tables to the list
      except IndexError:
        st.write(f"Error: Page {page_num} not found in the PDF.")

  return all_tables

def merge_parameter_tables(tables):
    if not tables:
        return None

    merged_table = []
    header_row = None

    for table in tables:
        if not table:
            continue

        if not header_row:
            header_row = table[0]
            merged_table.append(header_row)

        for row in table[1:]:
            merged_table.append(row)

    # Convert the merged table to a DataFrame
    df = pd.DataFrame(merged_table[1:], columns=merged_table[0])
    return df

def remove_rows_with_more_empty_values(df, threshold=8):
  empty_counts = df.isnull().sum(axis=1)

  # Filter rows with more empty values than the threshold
  filtered_df = df[empty_counts <= threshold]
  return filtered_df