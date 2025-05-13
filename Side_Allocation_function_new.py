import pandas as pd
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
    
###########################################################

def assigning_priority_for_group(df,priority_mapping_json):
    df_copy = df.copy()  
    df_copy['Priority'] = df_copy.apply(lambda row: priority_order(row, df_copy,priority_mapping_json), axis=1)
    return df_copy

def priority_order(row, df, priority_mapping_json):
    with open(priority_mapping_json, 'r') as file:
        mappings = json.load(file)

    value = row['Grouping']
    index = row.name
    value_alternative = row['Pin Alternate Name']

    # Debug check (optional)
    if (row['Electrical Type'] == 'Input' and value.strip().startswith("Port")):
        print(f"After Swapping : {value}, Alt Name: {value_alternative}")

    # 1. Highest priority: Direct mapping
    if value in mappings['priority_map']:
        return mappings['priority_map'][value]
    
    # 2. Clock-related cases
    for clock_type, priority in mappings['clock_map'].items():
        if clock_type in value:
            return priority
    
    # 3. Input + Port check (MUST COME BEFORE GENERIC PORT HANDLING!)
    if row['Electrical Type'] == 'Input' and value.strip().startswith("Port"):
        for alt_name, priority in mappings['swap_conditions'].items():
            if alt_name in str(value_alternative):
                # --- Define swap function OUTSIDE the loop ---
                swap_pins_for_that_row(df, index, mappings['swap_conditions'])
                return priority
        return f"P_{value}"#"ZZ_Not_Assigned"  # Default if no swap condition matches
    
    # 4. Generic Port handling (now only for non-Input cases)
    if value.strip().startswith("Port"):
        try:
            port_number = int(value.split(' ')[1])
            return f"P_Port {port_number:02d}"
        except ValueError:
            return f"P_Port {value.split(' ')[1]}"
    
    # 5. Default case
    return None

def swap_pins_for_that_row(df, index, swap_conditions):
    current_display = df.loc[index, 'Pin Display Name']
    current_alternate = df.loc[index, 'Pin Alternate Name']
    
    # Find which swap_condition key is present in the alternate name
    for key in swap_conditions.keys():
        if key in current_alternate:
            # Extract the matching part (e.g., "X1" from "P121/X1/INTP1")
            matched_part = key
            
            # Swap ONLY the matched part with display name
            new_alternate = current_alternate.replace(matched_part, current_display)
            new_display = matched_part
            
            df.loc[index, 'Pin Display Name'] = new_display
            df.loc[index, 'Pin Alternate Name'] = new_alternate
            return
        
#######################################################


def assigning_side_for_priority(df):
    df_copy = df.copy()
    df_new = filter_and_sort_by_priority(df_copy)

    # Assign side
    df_new['Side'] = df_new.apply(lambda row: allocate_pin_side_by_priority(row, df_new), axis=1)

    # Assign order (same logic for both sides)
    df_new = assigning_ascending_order_for_similar_group(df_new)

    return df_new.reset_index(drop=True)

def filter_and_sort_by_priority(df):

    if df.empty:
        print("The DataFrame is empty; skipping sorting.")
        return df  # Return the empty DataFrame as is

    print(f"Descriptive Columns in DataFrame: {list(df.columns)}")  # Print all column names
    sorted_df = df.sort_values(by='Priority', ascending=True).reset_index(drop=True)
    return sorted_df


def allocate_pin_side_by_priority(row, df):
    """
    Assigns each pin (row) to 'Left' or 'Right' side based on its Priority group,
    ensuring balanced distribution. Prioritizes filling the Left side first and
    avoids splitting Priority groups. Returns an error message if total pins exceed 80.
    """
    total_rows = len(df)
    if total_rows > 80:
        return "Some error Occurred"

    grouped_indices = df.groupby('Priority').indices
    left, right = [], []
    left_limit = (total_rows + 1) // 2  # ceiling division
    last_side = 'Left'

    for group in list(grouped_indices.values()):
        if last_side == 'Left' and len(left) + len(group) <= left_limit:
            left.extend(group)
        else:
            right.extend(group)
            last_side = 'Right'

    # Optional: diagnostic output
    print(f"\nPin Distribution:")
    print(f"Total pins: {total_rows}")
    print(f"Left side: {len(left)} pins")
    print(f"Right side: {len(right)} pins")

    return 'Left' if row.name in left else 'Right'

import re

def sort_by_pin_name_pattern(df, column_name='Pin Display Name', ascending=True):
    """
    Sorts a DataFrame of pins based on naming patterns:
    - Format 1: 'ABC_123' → sorted by base and number
    - Format 2: 'PA15'   → sorted by letter prefix and number
    - Otherwise falls back to simple alphabetical sorting
    """

    def extract_sort_keys(name):
        # Match 'ABC_123' pattern
        if '_' in name:
            parts = name.rsplit('_', 1)
            if parts[-1].isdigit():
                return parts[0], int(parts[1])
        # Match 'PA15' pattern
        match = re.match(r'^([A-Za-z]+)(\d+)$', name)
        if match:
            return match.group(1), int(match.group(2))
        # Fallback: treat whole name as base, no number
        return name, float('inf')

    df = df.copy()
    df['__sort_keys__'] = df[column_name].apply(extract_sort_keys)

    return df.sort_values(by='__sort_keys__', ascending=ascending).drop(columns='__sort_keys__')

def assigning_ascending_order_for_similar_group(df, column_name='Pin Display Name'):
    """
    Applies structured sorting to each Priority group in the DataFrame
    using smart pin name sorting logic.
    """
    return df.groupby('Priority', group_keys=False).apply(
        lambda group: sort_by_pin_name_pattern(group, column_name=column_name, ascending=True)
    ).reset_index(drop=True)

##########################################



def partitioning(df_last, max_rows_per_part=80):

    df_Part_A = pd.DataFrame()
    port_df_side_added = pd.DataFrame()
    Port_Part_1 = pd.DataFrame()
    Port_Balance_1 = pd.DataFrame()
    Port_Balance_2 = pd.DataFrame()
    Port_Balance_3 = pd.DataFrame()
    Port_Balance_4 = pd.DataFrame()
    Port_Balance_5 = pd.DataFrame()

    # Step 1: Filter and sort by priority
    df = filter_and_sort_by_priority(df_last)

    # Step 2: Handle power pins
    df['Side'] = df.apply(allocate_pin_side_by_priority.filter_out_power_pins, args=(df,), axis=1)
    power_df = df[df['Side'].isin(['Left', 'Right'])]
    df.loc[power_df.index, 'Side'] = power_df['Side']

    print("Power DataFrame:", power_df)

    # Step 3: Handle unfilled rows
    unfilled_df = df[df['Side'].isna()]
    number_of_rows_left = len(unfilled_df)
    print(f"Length of unfilled DataFrame: {number_of_rows_left}")

    # Initialize result tables
    df_Part_A = pd.DataFrame()
    port_df_side_added = pd.DataFrame()
    port_tables = {}

    if number_of_rows_left <= max_rows_per_part:
        print("Only one extra Part")
        df_Part_A = filter_and_sort_by_priority(unfilled_df)
        df_Part_A['Side'] = df_Part_A.apply(lambda row: allocate_pin_side_by_priority(row, df_Part_A), axis=1)
        df.loc[unfilled_df.index, 'Side'] = df_Part_A['Side'].values

        if df['Side'].isna().sum() > 0:
            print("Some pins are still unassigned:")
            print(df[df['Side'].isna()])

    elif number_of_rows_left > max_rows_per_part and any(unfilled_df['Priority'].str.startswith('P_Port')):
        port_df = unfilled_df[unfilled_df['Priority'].str.startswith('P_Port')]
        other_df = unfilled_df[~unfilled_df.index.isin(port_df.index)]

        print(f"Port df length: {len(port_df)}, Other df length: {len(other_df)}")
        combined_df = pd.concat([port_df, other_df], ignore_index=True)

        # Add logic for splitting the data into parts based on the number of rows
        num_parts = (len(combined_df) + max_rows_per_part - 1) // max_rows_per_part
        for i in range(num_parts):
            start = i * max_rows_per_part
            end = start + max_rows_per_part
            part_df = combined_df.iloc[start:end]
            port_tables[f"Port Table - {i + 1}"] = part_df

    else:
        print("You will have to create more Parts manually.")

    # Step 4: Build final DataFrame dictionary
    df_dict = {
        'Power Table': power_df,
        'Part A Table': df_Part_A,
        'Port Table': port_df_side_added,
        'Others Table': df[df['Side'].isna()],
        'Port Table - 1': Port_Part_1,
        'Port Table - 2': Port_Balance_1,
        'Port Table - 3': Port_Balance_2,
        'Port Table - 4': Port_Balance_3,
        'Port Table - 5': Port_Balance_4,
        'Port Table - 6': Port_Balance_5
    }

    # Add Port Table - X dynamically if more parts are created
    df_dict.update(port_tables)

    # Final consistency check
    total_processed = sum(len(v) for v in df_dict.values())
    if total_processed != len(df):
        print("Mismatch in total row count!")
        print(f"Total processed: {total_processed}, Original: {len(df)}")

    return df_dict

#####################################################


def assigning_side_for_priority_for_dataframes_within_dictionary(dfs):
    final_dfs = {}

    for title, df in dfs.items():
        df_copy = df.copy()

        df_new = assigning_side_for_less_than_80_pin_count(df_copy)
        
        # Initialize an empty list to hold the sorted dataframes
        sorted_dfs = []

        # Loop over both sides
        for side in ['Left', 'Right']:
            side_df = df_new[df_new['Side'] == side]
            sorted_side_df = assigning_ascending_order_for_similar_group(side_df)
            sorted_dfs.append(sorted_side_df)

        # Concatenate the two sorted DataFrames back together
        final_df = pd.concat(sorted_dfs).reset_index(drop=True)
        
        # Store the modified DataFrame in the final dictionary
        final_dfs[title] = final_df
    
    return final_dfs

def assigning_side_for_less_than_80_pin_count(df):
    df_Part = filter_and_sort_by_priority(df)
    df_Part['Side'] = df_Part.apply(lambda row: allocate_pin_side_by_priority(row, df_Part), axis=1)

    return df_Part

#########################################


def final_filter(df):

    # Step 1: Remove 'Grouping' column if it exists
    if "Grouping" in df.columns:
        df = df.drop(columns=["Grouping"])

    # Step 2: Rename 'Priority' to 'Grouping' if it exists
    if "Priority" in df.columns:
        df = df.rename(columns={"Priority": "Grouping"})

    # Step 3: Replace NaN with empty string
    df = df.fillna("")

    # Step 4 & 5: Clean string values across the DataFrame
    df = df.applymap(lambda x: str(x).strip().replace('  ', ' ').replace('\n', ' ').replace(' ', '_'))

    # Step 6: Convert 'Pin Designator' values to integers if they are numeric
    if "Pin Designator" in df.columns:
        df["Pin Designator"] = df["Pin Designator"].apply(
            lambda x: int(float(x)) if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).isdigit()) else x
        )

    return df

