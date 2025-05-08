from grouping_algorithm import *
import pandas as pd
import json
from pandas import *
from dotenv import load_dotenv
import google.generativeai as genai
import os
from fuzzywuzzy import process
import glob

def check_excel_format_for_grouping(df):
  
  try:
    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping']

    if set(required_columns) == set(df.columns):
      return True, df
    elif set(required_columns[:-1]) == set(df.columns):  # Check for missing 'Grouping' column
      df['Grouping'] = ' '
      #df.to_excel(excel_path, index=False)
      return True, df
    else:
      print("Incorrect extraction format.")
      return False, df
  except Exception as e:
    print(f"Error reading Excel file: {e}")
    return False, df 
  

def check_excel_format_for_type(df):
  
  try:
    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name']

    if set(required_columns) == set(df.columns):
      return True, df
    elif set(required_columns[:-1]) == set(df.columns):  # Check for missing 'Grouping' column
      df['Electrical Type'] = ' '
      #df.to_excel(excel_path, index=False)
      return True, df
    else:
      print("Incorrect extraction format.")
      return False, df
  except Exception as e:
    print(f"Error reading Excel file: {e}")
    return False, df 


def assigning_grouping_as_per_database(old_df, json_paths):
    df = old_df.copy()
    
    try:
        # Load JSON files
        with open(json_paths['Input'], 'r') as f:
            input_label_map = json.load(f)
        with open(json_paths['Power'], 'r') as f:
            power_label_map = json.load(f)
        with open(json_paths['Output'], 'r') as f:
            output_label_map = json.load(f)
        with open(json_paths['I/O'], 'r') as f:
            io_label_map = json.load(f)
        with open(json_paths['Passive'], 'r') as f:
            passive_label_map = json.load(f)

        def clean_string(s):
            """Remove ALL whitespace and normalize case"""
            return ''.join(str(s).split()).upper()

        def get_label(name, label_maps):
            clean_name = clean_string(name)
            for label_map in label_maps:
                for label, names in label_map.items():
                    if clean_name in [clean_string(n) for n in names]:
                        return label
            print(f"Warning: No match for '{name}' (cleaned as '{clean_name}')")
            return None

        df['Grouping'] = None

        for index, row in df.iterrows():
            pin_name = str(row['Pin Display Name'])
            # PROPER cleaning of Electrical Type
            elec_type = clean_string(row['Electrical Type'])

            if elec_type == "INPUT":
                label = get_label(pin_name, [input_label_map, io_label_map])
            elif elec_type == "POWER":
                label = get_label(pin_name, [power_label_map])
            elif elec_type == "OUTPUT":
                label = get_label(pin_name, [output_label_map, io_label_map])
            elif elec_type == "I/O":
                label = get_label(pin_name, [io_label_map])
            elif elec_type == "PASSIVE":
                label = get_label(pin_name, [passive_label_map])
            else:
                print(f"Unknown Electrical Type: '{row['Electrical Type']}' (cleaned as '{elec_type}')")
                label = None

            if label:
                df.at[index, 'Grouping'] = label

    except Exception as e:
        print(f"Error: {e}")
    
    return df


def assigning_pin_type_as_per_database(old_df, json_paths):
    df = old_df.copy()
    
    try:
        # Load all JSON files
        label_maps = {}
        for key, path in json_paths.items():
            with open(path, 'r') as f:
                label_maps[key] = json.load(f)

        def clean_string(s):
            """Remove ALL whitespace (spaces, \n, \t) and normalize case"""
            return ''.join(str(s).split()).upper()

        def get_file_name(pin_name):
            clean_pin = clean_string(pin_name)
            matches = set()
            
            # Check each JSON file for the pin name
            for file_name, label_map in label_maps.items():
                for label, names in label_map.items():
                    # Clean all names in JSON before comparison
                    if clean_pin in [clean_string(item) for item in names]:
                        matches.add(file_name)
            
            # Handle conflicts and missing pins
            if len(matches) > 1:
                print(f"Conflict: Pin '{pin_name}' (cleaned: '{clean_pin}') found in multiple files: {matches}")
                return None
            elif len(matches) == 1:
                return matches.pop()
            else:
                print(f"Warning: Pin '{pin_name}' (cleaned: '{clean_pin}') not found in any JSON file")
                return None

        # Apply with proper cleaning
        df['Electrical Type'] = df['Pin Display Name'].apply(
            lambda x: get_file_name(str(x).strip())
        )

        print("Pin types assigned successfully.")

    except Exception as e:
        print(f"Error: {str(e)}")
    
    return df

def assigning_grouping_as_per_LLM(pin_table):

    load_dotenv()
    model = genai.GenerativeModel("gemini-pro")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=GOOGLE_API_KEY)

    # Prompt to LLM
    input = f"Guess what category this device can be just by referring to the pin table. Here is your pin table {pin_table}"
    response = model.generate_content(input)
    print(response.text)
    pin_grouping_table = pin_table

    # Return the response and an empty DataFrame (uniform with other functions)
    return response, pin_table  

def assigning_grouping_as_per_algorithm(df):
    df['Grouping'] = df['Pin Display Name'].apply(group_port_pins)
    #df['Grouping'] = df.apply(group_power_pin, axis=1)
    mask = df['Grouping'].isna()  # Create a mask for NaN values in 'Grouping'
    df.loc[mask, 'Grouping'] = df[mask].apply(group_other_io_pins, axis=1)
    mask = df['Grouping'].isna()  # Create a mask for NaN values in 'Grouping'
    df.loc[mask, 'Grouping'] = df[mask].apply(group_power_pins, axis=1)  # Apply group_power_pin only to NaN rows
    mask = df['Grouping'].isna()
    df.loc[mask, 'Grouping'] = df[mask].apply(group_output_pins, axis=1)
    mask = df['Grouping'].isna()
    df.loc[mask, 'Grouping'] = df[mask].apply(group_input_pins, axis=1)
    mask = df['Grouping'].isna()
    df.loc[mask, 'Grouping'] = df[mask].apply(group_passsive_pins, axis=1)    

    return df


def check_empty_groupings(df):
    empty_groupings = df[df['Grouping'].isna()]
    return empty_groupings

def check_empty_pintypes(df):
    empty_electrical_type = df[df['Electrical Type'].isna()]
    return empty_electrical_type

def get_suggestions(user_input, json_data):

    key_matches = process.extract(user_input, json_data.keys(), limit=5)
    # Step 2: Create a dictionary to store the number of good matches for each key
    key_good_matches = {}
    
    # Step 3: Calculate the number of good matches for each key
    for key, _ in key_matches:
        good_matches = 0
        for value in json_data[key]:
            match_score = process.extractOne(user_input, [value])[1]
            if match_score > 0:  # Count any match (no threshold)
                good_matches += 1
        key_good_matches[key] = good_matches
    
    # Step 4: Sort the keys first by match percentage (descending), then by number of good matches (descending)
    sorted_keys = sorted(key_matches, key=lambda x: (-x[1], -key_good_matches[x[0]]))
    
    limit = 5
    # Step 5: Return the top `limit` suggestions
    return sorted_keys[:limit]



def load_json_files(file_paths):
    data = {}
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            data.update(json.load(file))
    return data

def load_json_files_with_type_labels(directory):
    json_data = {}
    json_files = glob.glob(os.path.join(directory, '*.json'))
    for file_path in json_files:
        with open(file_path, 'r') as file:
            data = json.load(file)
            json_data[file_path] = data
    return json_data

def save_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def remove_electrical_type(df):
    columns_removed = []
    
    # Remove "Electrical Type" column if it exists
    if "Electrical Type" in df.columns:
        df = df.drop(columns=["Electrical Type"])
        columns_removed.append("Electrical Type")
        print("'Electrical Type' column has been removed.")
    else:
        print("'Electrical Type' column is not present in the DataFrame.")
    
    # Remove "Grouping" column if it exists
    if "Grouping" in df.columns:
        df = df.drop(columns=["Grouping"])
        columns_removed.append("Grouping")
        print("'Grouping' column has been removed.")
    else:
        print("'Grouping' column is not present in the DataFrame.")
    
    # Return the updated DataFrame and a flag indicating if any columns were removed
    return df, False
   