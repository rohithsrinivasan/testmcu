import pdfplumber
import tabula
import numpy as np
import pandas as pd
import streamlit as st

'''def find_pages_between_keywords(pdf_path, start_keyword, end_keyword):
    with pdfplumber.open(pdf_path) as pdf:
        start_page, end_page = None, None
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text().lower()
            if start_keyword in text and start_page is None:
                start_page = page_num
            if end_keyword in text and end_page is None:
                end_page = page_num
            if start_page and end_page:
                break

        # Return a list containing the page number(s)
        if start_page == end_page:
            return [start_page]
        else:
            return list(range(start_page, end_page)) if start_page and end_page else []'''

def find_pages_between_keywords(pdf_path, start_keyword, end_keyword):
    with pdfplumber.open(pdf_path) as pdf:
        start_page, end_page = None, None
        # Iterate through all the pages in the PDF
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text().lower()
            
            # Update the start_page to the latest occurrence of the start_keyword
            if start_keyword in text:
                start_page = page_num
            
            # Update the end_page to the latest occurrence of the end_keyword
            if end_keyword in text:
                end_page = page_num

        # Return a list containing the page numbers from start_page to end_page
        if start_page and end_page:
            # If start_page and end_page are the same, return that single page
            if start_page == end_page:
                return [start_page]
            else:
                return list(range(start_page, end_page + 1))  # inclusive of end_page
        else:
            return []


        
def extracting_tables_in_pages(file_path, my_list_of_pages):
    dfs = tabula.read_pdf(file_path, pages= my_list_of_pages, multiple_tables=True, lattice= True)
    dfs = [df for df in dfs if not df.empty and df.dropna(how='all').shape[0] > 0]
      #dfs = [df for df in dfs if any(col in df.columns for col in ["Orderable Part Number", "Number of Pins", "Package", "Package Code/POD Number"])]
    modified_dfs = []
    for df in dfs:
        modified_df = df.replace(to_replace=r'^Unnamed:.*', value=np.nan, regex=True)
        # Check if all columns are unnamed (NaN or 'Unnamed:')
        if all(modified_df.columns.str.contains('^Unnamed:')):
            # Drop completely empty rows (those with all NaN values)
            modified_df = modified_df.dropna(how='all')
            # Take the first non-empty row and use it as the header
            if not modified_df.empty:
                new_header = modified_df.iloc[0]  # First row
                modified_df = modified_df[1:]  # Remove the first row from data
                modified_df.columns = new_header  # Set new header

        #print(f"modified_df_0 : {modified_df}")

        # Convert column names to strings, filter out NaN and 'Unnamed'
        filtered_columns = [str(col) for col in modified_df.columns if pd.notna(col) and "Unnamed" not in str(col)]

        # Join filtered column names into a string
        column_string_variable = ''.join(filtered_columns)

        modified_df = modified_df.apply(lambda x: pd.Series(x.dropna().values), axis=1)
        #print(f"modified_df_1 : {modified_df}")
        modified_df = modified_df.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x)
        #print(f"modified_df_2 : {modified_df}")
        #modified_df = modified_df.drop(modified_df[modified_df.isin(['Designator']).any(axis=1)].index)

        if modified_df.shape[1] == 4 and 'orderable part' in column_string_variable.lower():
            #print("DataFrame has 4 columns as expected")
            # Assign expected column names ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name']
            modified_df.columns = ["Orderable Part Number", "Number of Pins", "Package", "Package Code/POD Number"]
            modified_dfs.append(modified_df)
            #print(f"modified_df_3 : {modified_df}")

        elif modified_df.shape[1] == 4 and 'Pin Designator' in column_string_variable:
            print("It must be a pin table")

        else:
            print(f"Unexpected number of columns: {modified_df.shape[1]}")

    #if len(modified_dfs) == 1:
        #return modified_dfs[0]
    
    return modified_dfs

def before_merging(dfs):

    print("Number of DataFrames:", len(dfs))

    if not dfs:
        print("No DataFrames provided.")
        return False 

    for df in dfs:
        print("Processing DataFrame:")
        #print(df.head())  # Print the first few rows of the DataFrame

        # Replace unnamed columns with NaN and drop NaN values
        modified_df = df.replace(to_replace=r'^Unnamed:.*', value=np.nan, regex=True)
        print("After replacing unnamed columns with NaN:", modified_df.head())

        #modified_df = modified_df.apply(lambda x: pd.Series(x.dropna().values), axis=1)
        #print("After dropping NaN values:", modified_df.head())

        #modified_df = modified_df.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x)
        #print("After converting to integers:", modified_df.head())

    if len(dfs) > 1:
        print("Checking if column names are the same for all DataFrames...")

        column_names = [df.columns.tolist() for df in dfs]

        # Check if all column names are the same
        if len(set(map(tuple, column_names))) != 1:
            print("Column names are not the same.")
            return False 
    
    print("All checks passed.")
    return True 


def merge_tables(dfs):
        merged_df = pd.concat(dfs, ignore_index=True)
        return merged_df
    

def search_for_part_number_in_the_indexing_table(merged_table, part_number):
    #print(f"merged table : {merged_table}")
    part_number_row = merged_table[merged_table['Orderable Part Number'] == part_number]
    if not part_number_row.empty:
        number_of_pins = part_number_row['Number of Pins'].values[0]
        package_type = part_number_row['Package'].values[0]
        package_code = part_number_row['Package Code/POD Number'].values[0]
        return part_number, number_of_pins, package_type, package_code
    else:
        return None, None, None, None

def create_selectbox_for_user_to_select(merged_table):
    # Create a formatted dropdown of valid part numbers
    merged_table['Formatted Part Number'] = merged_table.apply(
        lambda row: f"{row['Orderable Part Number']} ({row['Number of Pins']}-{row['Package']})", axis=1
    )

    part_numbers = merged_table['Formatted Part Number'].unique()
    selected_part_number = st.selectbox("Select a part number", part_numbers)

    # Extract the original part number from the selected formatted string
    original_part_number = selected_part_number.split(" ")[0]

    # Search for part number details
    part_number, number_of_pins, package_type, package_code = search_for_part_number_in_the_indexing_table(
        merged_table, original_part_number)
    
    if part_number is not None:
        return part_number, number_of_pins, package_type, package_code
    else:
        st.error("Part number not found.")
            
