import pandas as pd
from partitioning_functions import *
import json


def check_excel_format_dict(df_dict, required_columns, additional_column):
    flag = True
    
    for key, df in df_dict.items():
        if set(required_columns) != set(df.columns):
            if set(required_columns[:-1]) == set(df.columns):
                df[additional_column] = ' '
            else:
                print(f"Incorrect extraction format for DataFrame '{key}'.")
                flag = False
    
    return flag, {key: df for key, df in df_dict.items()}

def check_excel_format(df, required_columns, additional_column):
    try:
        # If df is a DataFrame
        if isinstance(df, pd.DataFrame):
            if set(required_columns) == set(df.columns):
                return True, df
            elif set(required_columns[:-1]) == set(df.columns):
                df[additional_column] = ' '
                return True, df
            else:
                print("Incorrect extraction format.")
                return False, df
        
        # If df is a dictionary of DataFrames
        elif isinstance(df, dict):
            return check_excel_format_dict(df, required_columns, additional_column)
        
        else:
            print("Invalid input type: must be a DataFrame or dictionary of DataFrames.")
            return False, df

    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return False, df

########################################################################################

# Load the JSON file with priority mappings
with open('priority_mappings_2.json', 'r') as file:
    mappings = json.load(file)

def priority_order(row, df):
    value = row['Grouping']
    index = row.name  # Get the row's index
    value_alternative = row['Pin Alternate Name']

    # Direct mapping based on value
    if value in mappings['priority_map']:
        return mappings['priority_map'][value]
    
    # Clock-related cases
    for clock_type, priority in mappings['clock_map'].items():
        if clock_type in value:
            return priority
    
    # Port handling
    if value.startswith("Port"):
        try:
            port_number = int(value.split(' ')[1])
            return f"P_Port {port_number:02d}"
        except ValueError:
            return f"P_Port {value.split(' ')[1]}"

    # Port-specific checks for Input type
    if row['Electrical Type'] == 'Input' and value.startswith("Port"):
        for alt_name, priority in mappings['swap_conditions'].items():
            if alt_name in value_alternative:
                swap_pins_for_that_row(df, index)
                return priority

        return "ZZ_Not_Assigned"
    
    # Default case
    return None


def swap_pins_for_that_row(df, index):
    df.loc[index, 'Pin Display Name'], df.loc[index, 'Pin Alternate Name'] = df.loc[index, 'Pin Alternate Name'], df.loc[index, 'Pin Display Name']
    return

def assigning_priority_for_group(df):
    df_copy = df.copy()  
    df_copy['Priority'] = df_copy.apply(lambda row: priority_order(row, df_copy), axis=1)
    return df_copy

#################################################################
    
def filter_and_sort_by_priority(df):
    sorted_df = df.sort_values(by='Priority', ascending=True).reset_index(drop=True)
    return sorted_df

def filter_and_sort_by_priority(df):

    if df.empty:
        print("The DataFrame is empty; skipping sorting.")
        return df  # Return the empty DataFrame as is

    print(f"Descriptive Columns in DataFrame: {list(df.columns)}")  # Print all column names
    sorted_df = df.sort_values(by='Priority', ascending=True).reset_index(drop=True)
    return sorted_df



def side_allocation(row, df):
    total_rows = len(df)    
    if total_rows > 80:
        return f"Some error Occured"
    else:
        return allocate_small_dataframe(row, df)

def allocate_small_dataframe(row, df):
    grouped_indices = df.groupby('Priority').indices
    total_rows = len(df)
    left = []
    right = []
    left_limit = total_rows // 2 

    last_side = 'Left'  

    for group in grouped_indices.values():
        if last_side == 'Left' and len(left) + len(group) <= left_limit:
            left.extend(group)
        else:
            right.extend(group)
            last_side = 'Right'  

    if row.name in left:
        return 'Left'
    else:
        return 'Right'



def assigning_side_for_priority(df):
    df_copy = df.copy()
    df_new = filter_and_sort_by_priority(df_copy)
    df_new['Side'] = df_new.apply(lambda row: side_allocation(row, df_new), axis=1)
    
    # Apply sorting based on 'Side'
    ascending_order_df = df_new[df_new['Side'] == 'Left']
    ascending_order_df = assigning_ascending_order_for_similar_group(ascending_order_df)
    
    descending_order_df = df_new[df_new['Side'] == 'Right']
    descending_order_df = assigning_descending_order_for_similar_group(descending_order_df)
    
    # Concatenate the two sorted DataFrames back together
    final_df = pd.concat([ascending_order_df, descending_order_df]).reset_index(drop=True)
    
    return final_df

 
def assigning_ascending_order_for_similar_group(df):
    df_copy = df.copy()
    ascending_order_df = df_copy.groupby('Priority').apply(lambda group: group.sort_values('Pin Display Name'))
    ascending_order_df.reset_index(drop=True, inplace=True)
    return ascending_order_df 

def assigning_descending_order_for_similar_group(df):
    df_copy = df.copy()
    descending_order_df = df_copy.groupby('Priority').apply(lambda group: group.sort_values('Pin Display Name', ascending=False))
    descending_order_df.reset_index(drop=True, inplace=True)
    return descending_order_df


def process_dataframe(df_copy):
    # Create a new column 'Changed Grouping'
    df_copy['Changed Grouping'] = None

    # Function to get alphabetical inverse of the first letter
    def alphabetical_inverse(letter):
        if letter.isalpha() and letter.isupper():
            return chr(155 - ord(letter))  # A -> Z, B -> Y, etc.
        return letter

    # Function to get the alphabet corresponding to the reverse of a number (e.g., 01 -> Z, 05 -> V)
    def number_to_alphabet_inverse(number_str):
        if number_str.isdigit():
            num = int(number_str)
            if 1 <= num <= 26:
                return chr(91 - num)  # 1 -> Z, 2 -> Y, 3 -> X, ..., 26 -> A
        return number_str

    # Function to sort groups by 'Pin Display Name' in descending order for 'Right' side
    def assigning_descending_order_for_similar_group(group):
        return group.sort_values('Pin Display Name', ascending=False)
    
    def assigning_ascending_order_for_similar_group(group):
        return group.sort_values('Pin Display Name', ascending=True)    

    # Sort the right-side groups by 'Pin Display Name' in descending order
    right_side_group = df_copy[df_copy['Side'] == 'Right']
    sorted_right_group = right_side_group.groupby('Priority').apply(assigning_descending_order_for_similar_group)    

    # Iterate over the rows
    for index, row in df_copy.iterrows():
        priority = row['Priority']

        # For 'Left' side, keep the priority unchanged
        if row['Side'] == 'Left':
            df_copy.at[index, 'Changed Grouping'] = priority

        # For 'Right' side, modify the priority using the sorted 'Pin Display Name'
        elif row['Side'] == 'Right':
            # Fetch the sorted row from the 'sorted_right_group'
            sorted_row = sorted_right_group.loc[
                (sorted_right_group['Priority'] == priority) &
                (sorted_right_group['Pin Display Name'] == row['Pin Display Name'])
            ].iloc[0]

            # Change the first letter of the 'Priority' value to its alphabetical inverse
            first_letter = sorted_row['Priority'][0]
            inverse_first_letter = alphabetical_inverse(first_letter)

            # Check if the priority ends with a number
            if sorted_row['Priority'][-2:].isdigit():  # Assuming numbers are two digits
                num_part = sorted_row['Priority'][-2:]  # The last two characters (numbers)
                inverse_num_part = number_to_alphabet_inverse(num_part)

                # Reconstruct the priority with the inverse number and inverse first letter
                df_copy.at[index, 'Changed Grouping'] = inverse_first_letter + sorted_row['Priority'][1:-2] + inverse_num_part + "_" + num_part
            else:
                # If no number at the end, just change the first letter
                df_copy.at[index, 'Changed Grouping'] = inverse_first_letter + sorted_row['Priority'][1:]

    return df_copy


def Dual_in_line_as_per_Renesas(df):
    # Check if the input is a dictionary of DataFrames
    if isinstance(df, dict):
        df_copy_dict = {}  # Initialize a dictionary to store modified DataFrames
        
        # Iterate through each DataFrame in the input dictionary
        for table_name, df_copy in df.items():
            # Create a copy of the current DataFrame
            df_copy = df_copy.copy()
            # Process the DataFrame
            df_copy_dict[table_name] = process_dataframe(df_copy)
        
        return df_copy_dict  # Return the modified dictionary of DataFrames

    # If the input is not a dictionary, process the single DataFrame
    df_copy = df.copy()
    processed_dataframe = process_dataframe(df_copy)

    process_dataframe = process_dataframe.drop(['Grouping', 'Priority'], axis=1)
    print(f"Dataframe headers : {process_dataframe.head()}")

    return processed_dataframe

def Dual_in_line_as_per_Renesas(df):
    # Check if the input is a dictionary of DataFrames
    if isinstance(df, dict):
        df_copy_dict = {}  # Initialize a dictionary to store modified DataFrames
        
        # Iterate through each DataFrame in the input dictionary
        for table_name, df_copy in df.items():
            # Create a copy of the current DataFrame
            df_copy = df_copy.copy()
            # Process the DataFrame
            df_copy_dict[table_name] = process_dataframe(df_copy)

            for processed_table_name, processed_df in df_copy_dict.items():
                # Apply drop and rename to each DataFrame in the dictionary
                processed_df = processed_df.drop(['Grouping', 'Priority'], axis=1)
                processed_df = processed_df.rename(columns={'Changed_grouping': 'New_grouping'})
        
        # Update the dictionary with the modified DataFrame
        df_copy_dict[processed_table_name] = processed_df
        
        return df_copy_dict  # Return the modified dictionary of DataFrames

    # If the input is not a dictionary, process the single DataFrame
    df_copy = df.copy()
    final_df = process_dataframe(df_copy)
    final_df = final_df.drop(['Grouping', 'Priority'], axis=1)
    final_df = final_df.rename(columns={'Changed_grouping': 'New_grouping'})

    return final_df

def final_filter(df):
    # Remove leading/trailing whitespace and replace multiple spaces with single space
    df = df.applymap(lambda x: str(x).strip().replace('  ', ' '))

    # Remove newlines and convert to single word
    df = df.applymap(lambda x: x.replace('\n', ' ').replace(' ', '_'))

    return df