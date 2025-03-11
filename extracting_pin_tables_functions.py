import pdfplumber
import re
import pandas as pd
import tabula
import numpy as np
import json

def find_table_starting_and_stopping_based_on_pin_string(pdf_path, page_number_list, pin_keyword, package_keyword):

    
    with pdfplumber.open(pdf_path) as pdf:
        for page_number in page_number_list:
            if page_number > len(pdf.pages):
                print(f"Skipping page {page_number} - exceeds total number of pages ({len(pdf.pages)})")
                continue

            text = pdf.pages[page_number - 1].extract_text()
            #print(f"--- Page {page_number} Text ---")
            #print(text)  # Print the entire page text

            matching_lines = [line for line in text.split('\n')
                            if pin_keyword.lower() in line.lower() and package_keyword.lower() in line.lower()]

            #print(f"--- Matching lines on page {page_number} ---")
            #print(matching_lines)  # Print the matching lines    

            if matching_lines and len(matching_lines[0].split(" ")) == 2:
                for line in matching_lines:
                    words = line.split()
                    # Check if the line contains a valid section number with two words
                    if len(words) == 2 and re.match(r'^[A-Z0-9]\.\d+\.\d+$', words[0]):
                        #print("found target line")
                        section_number = words[0]
                        sections = section_number.split('.')
                        sections[-1] = str(int(sections[-1]) + 1)  # Increment the last section
                        next_section_number = '.'.join(sections)
                        #print(next_section_number)

                        new_next_section_number, ending_page_number = find_ending_page(pdf, page_number_list, next_section_number)

                        # Return the first matching page number and section details
                        return page_number, section_number, new_next_section_number, ending_page_number

    print(f"Keyword '{pin_keyword}' or '{package_keyword}' not found or no valid table number found in the specified pages.")
    return None


def find_ending_page(pdf, page_number_list, next_section_number):
    next_section_number = next_section_number.lower()

    for page_num in page_number_list:
        if page_num <= 0:
            continue
        text = pdf.pages[page_num - 1].extract_text().lower()
        if next_section_number in text:
            return next_section_number.upper(), page_num

    print(f"'{next_section_number}' not found in specified pages. Using 'Symbol Parameters' as ending point.")
    return "Symbol Parameters", page_number_list[-1]

def generate_list_of_page_numbers(start, end):
  if start > end:
    return None  # Invalid input: start > end

  return list(range(start, end + 1))

'''def extracting_pin_tables_in_pages(file_path, my_list_of_pages):
    #print(f"Pages to extract: {my_list_of_pages}")
    #dfs = tabula.read_pdf(file_path, pages= my_list_of_pages, multiple_tables=True, lattice= True)
    dfs = tabula.read_pdf(file_path, pages=my_list_of_pages, multiple_tables=True, lattice=True, encoding='ISO-8859-1')
    #print(f"Raw dataframe :{dfs}" )
    dfs = [df for df in dfs if not df.empty and df.dropna(how='all').shape[0] > 0]
    modified_dfs = []
    for df in dfs:
        #df = df.astype(str).apply(lambda x: x.str.encode('utf-8', 'ignore').str.decode('utf-8') if x.dtype == 'object' else x)

        modified_df = df.replace(to_replace=r'^Unnamed:.*', value=np.nan, regex=True)  # Replace column names starting with "Unnamed:" with NaN.
        modified_df = modified_df.apply(lambda x: pd.Series(x.dropna().values), axis=1)  # Rearrange each row to remove NaN values while keeping order.
        modified_df = modified_df.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x)  # Convert float values to integers if they have no decimal part.
        modified_df = modified_df.drop(modified_df[modified_df.apply(lambda row: row.astype(str).str.lower().isin(['designator']).any(), axis=1)].index)  # Drop rows containing "Designator" or "electrical type" (case insensitive).
        modified_df = modified_df.dropna(how='all')  # Remove rows that have only NaN values.
        modified_df_columns = ''.join(modified_df.columns.astype(str))
        print(f"modified_df_columns: {modified_df_columns}")



        print(f"modified_df :{modified_df}")

        if modified_df.shape[1] == 4:
            #print("DataFrame has 4 columns as expected")
            # Assign expected column names ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name']
            #modified_df.columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name']
            modified_dfs.append(modified_df)
        else:
            print(f"Unexpected number of columns: {modified_df.shape[1]}")

    #if len(modified_dfs) == 1:
        #return modified_dfs[0]
    return modified_dfs'''

def extracting_pin_tables_in_pages(file_path, my_list_of_pages):
    dfs = tabula.read_pdf(file_path, pages= my_list_of_pages, multiple_tables=True, lattice= True, encoding='ISO-8859-1')
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

        if modified_df.shape[1] == 4 and 'electrical' in column_string_variable.lower():
            #print("DataFrame has 4 columns as expected")
            # Assign expected column names ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name']
            #modified_df.columns = ["Orderable Part Number", "Number of Pins", "Package", "Package Code/POD Number"]
            modified_df.columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name']            
            modified_dfs.append(modified_df)
            #print(f"modified_df_3 : {modified_df}")

        elif modified_df.shape[1] == 4 and 'orderable part' in column_string_variable.lower():
            print("It must be a part number indexing table")

        else:
            print(f"Unexpected number of columns: {modified_df.shape[1]}")

    #if len(modified_dfs) == 1:
        #return modified_dfs[0]
    
    return modified_dfs


def extract_table_as_text(pdf_path, page_number_list, start_string, ending_string):
    with pdfplumber.open(pdf_path) as pdf:
        texts = []
        capturing = False
        extracted_text = ""
        
        for page_number in page_number_list:
            if page_number > len(pdf.pages):
                continue
            page = pdf.pages[page_number - 1]
            text = page.extract_text()
            
            if text:
                if capturing:
                    end_index = text.find(ending_string)
                    if end_index != -1:
                        extracted_text += text[:end_index + len(ending_string)]
                        texts.append(extracted_text)
                        capturing = False
                        extracted_text = ""
                    else:
                        extracted_text += text
                if start_string in text and not capturing:
                    start_index = text.find(start_string)
                    extracted_text = text[start_index:]
                    capturing = True
                    end_index = text.find(ending_string, start_index)
                    if end_index != -1:
                        extracted_text = text[start_index:end_index + len(ending_string)]
                        texts.append(extracted_text)
                        capturing = False
                        extracted_text = ""
        
        if capturing:
            texts.append(extracted_text)
        
        return "\n".join(texts) if texts else None

def text_filter(input_string):
    lines = input_string.splitlines()
    filtered_lines = [line for line in lines if not (line.startswith('Pin') or line.startswith('Designator') or line.startswith('Name'))]

    return '\n'.join(filtered_lines)


def df_to_string(df):
  string_representation = ""
  for index, row in df.iterrows():
    row_string = " ".join(str(value) for value in row)
    string_representation += row_string + "\n"
  return string_representation    


def combine_dataframes_and_print_dictionary(dfs):

    #if len(dfs) == 1:
        #return dfs[0]
    
    # Create a dictionary of DataFrame indices and their string representations
    df_strings = {i + 1: df_to_string(df) for i, df in enumerate(dfs)}

    # Generate all possible combinations of DataFrame indices and combine their text
    combo_dict = {}
    for i in range(len(df_strings)):
        for j in range(i + 1, len(df_strings) + 1):
            combo_keys = tuple(range(i + 1, j + 1))
            combo_values = "\n".join([df_strings[k] for k in combo_keys])
            combo_dict[combo_keys] = combo_values

    num = len (combo_dict)    
    return combo_dict, num

def filter_top_3_by_size(combo_dict, input_string):
    size_diffs = {combo_keys: abs(len(combo_value) - len(input_string)) 
                  for combo_keys, combo_value in combo_dict.items()}
    sorted_size_diffs = dict(sorted(size_diffs.items(), key=lambda x: x[1]))
    top_3 = {k: sorted_size_diffs[k] for k in list(sorted_size_diffs)[:3]}  
    return top_3

def filter_combo_dict_based_on_size_filter(dict1, dict2):
    # Retain only the key-value pairs in dict1 if the key is also present in dict2
    filtered_dict = {key: dict1[key] for key in dict2 if key in dict1}
    return filtered_dict

def compare_input_string_with_value_string(input_dict, input_string):
    input_lines = set(input_string.splitlines())
    result = {}

    for key, value_string in input_dict.items():
        value_lines = set(value_string.splitlines())
        extra_lines = max(abs(len(value_lines - input_lines)), abs(len(input_lines - value_lines)))
        result[key] = extra_lines

    '''min_key = min(result, key=result.get)
    return result, min_key'''

    min_value = min(result.values())
    min_keys = [key for key, value in result.items() if value == min_value]

    if len(min_keys) > 1:
        # If multiple keys have the same minimum difference, choose the shortest key
        min_key = min(min_keys, key=lambda k: len(str(k)))
    else:
        min_key = min_keys[0]

    return result, min_key

#Min key value should not disturb the result{dictionary}

def get_dataframes_from_tuple(dataframes_list, index_tuple):

    if any(i > len(dataframes_list) or i < 1 for i in index_tuple):
        raise IndexError("Index out of range of DataFrame list.")

    selected_dataframes = [dataframes_list[i-1] for i in index_tuple]
    number = len(selected_dataframes)
    
    return selected_dataframes, number



def find_matching_dfs(dfs, table_as_text):
   
    #setting this for easy comparison
    target_words = set(table_as_text.split())
    # Create a dictionary of table numbers (index) and DataFrame strings
    df_strings = {i + 1: df_to_string(df) for i, df in enumerate(dfs)}
    
    # Generate all possible combinations of DataFrame strings and combine them
    combo_dict = {}
    for i in range(len(df_strings)):
        for j in range(i + 1, len(df_strings) + 1):
            combo_keys = tuple(range(i + 1, j + 1))
            combo_values = "\n".join([df_strings[k] for k in combo_keys])
            combo_dict[combo_keys] = combo_values


    # Find the best match
    # Initialize variables to track the best match
    best_match_keys = None
    max_word_matches = 0
    min_extra_noise = float('inf')
    
    # Iterate through the combinations and find the best match
    for keys, combined_text in combo_dict.items():
        combined_words = set(combined_text.split())
        
        # Find words that match the target
        matching_words = combined_words & target_words
        word_match_count = len(matching_words)
        
        # Extra noise is the number of words in combined_text that don't match table_as_text
        extra_noise = len(combined_words - target_words)
        
        # Update best match based on match count and noise
        if word_match_count > max_word_matches or (word_match_count == max_word_matches and extra_noise < min_extra_noise):
            best_match_keys = keys
            max_word_matches = word_match_count
            min_extra_noise = extra_noise

    return best_match_keys
