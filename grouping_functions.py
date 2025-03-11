from grouping_algorithm import *
import pandas as pd
import json
from pandas import *
from dotenv import load_dotenv
import google.generativeai as genai
import os
from fuzzywuzzy import process
import glob

def check_excel_format(df):
  
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
  
def assigning_grouping_as_per_database(old_df, json_paths):
    df = old_df.copy()
    
    try:
        # Load all JSON files
        with open(json_paths['input'], 'r') as f:
            input_label_map = json.load(f)
        with open(json_paths['power'], 'r') as f:
            power_label_map = json.load(f)
        with open(json_paths['output'], 'r') as f:
            output_label_map = json.load(f)
        with open(json_paths['io'], 'r') as f:
            io_label_map = json.load(f)
        with open(json_paths['passive'], 'r') as f:
            passive_label_map = json.load(f)

        # Define a generic function to search for a label in all JSON files
        def get_label(name, label_maps):
            name = name.strip()
            for label_map in label_maps:
                for label, names in label_map.items():
                    if name in [item.strip() for item in names]:
                        return label
            print(f"Warning: Could not find a matching label for {name} in any JSON file.")
            return None

        # Apply the correct function based on Electrical Type
        df['Grouping'] = None  # Initialize the Grouping column with None

        for index, row in df.iterrows():
            if row['Electrical Type'] == "Input":
                label = get_label(row['Pin Display Name'], [input_label_map, io_label_map, power_label_map, output_label_map, passive_label_map])
            elif row['Electrical Type'] == "Power":
                label = get_label(row['Pin Display Name'], [power_label_map, io_label_map, input_label_map, output_label_map, passive_label_map])
            elif row['Electrical Type'] == "Output":
                label = get_label(row['Pin Display Name'], [output_label_map, io_label_map, input_label_map, power_label_map, passive_label_map])
            elif row['Electrical Type'] == "I/O":
                label = get_label(row['Pin Display Name'], [io_label_map, input_label_map, power_label_map, output_label_map, passive_label_map])
            elif row['Electrical Type'] == "Passive":
                label = get_label(row['Pin Display Name'], [passive_label_map, io_label_map, input_label_map, power_label_map, output_label_map])
            else:
                label = None  # Handle unknown Electrical Types

            if label is not None:
                df.at[index, 'Grouping'] = label

        print("Labels assigned to Grouping column successfully.")

    except Exception as e:
        print(f"Error processing files: {e}")

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
   