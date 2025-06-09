import pandas as pd
import json
import re

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
    pin_display_name = row['Pin Display Name']

    # print(f"\n--- DEBUG: Processing {pin_display_name} ---")
    # print(f"Grouping: '{value}'")
    # print(f"Electrical Type: '{row['Electrical Type']}'")
    # print(f"Pin Alternate Name: '{value_alternative}'")

    # 1. Highest priority: Direct mapping
    if value in mappings['priority_map']:
        #print(f"Step 1: Direct mapping found - returning {mappings['priority_map'][value]}")
        return mappings['priority_map'][value]
    #else:
    #    print("Step 1: No direct mapping found")
    
    # 2. Clock-related cases
    clock_found = False
    for clock_type, priority in mappings['clock_map'].items():
        if clock_type in value:
            print(f"Step 2: Clock mapping found - returning {priority}")
            return priority
    #print("Step 2: No clock mapping found")
    
    # 3. Input + Port check 
    input_port_condition = (row['Electrical Type'] == 'Input' or row['Electrical Type'] == 'I/O') and value.strip().startswith("Port")
    #print(f"Step 3: Input/IO + Port condition: {input_port_condition}")
    #print(f"  - Electrical Type check: {row['Electrical Type'] == 'Input' or row['Electrical Type'] == 'I/O'}")
    #print(f"  - Port check: {value.strip().startswith('Port')}")
    
    if input_port_condition:
        #print("Step 3: Entering Input/IO + Port handling")
        
        # 3A. FIRST: Check for mixed port assignment (PXX vs PXXX)
        #print("Step 3A: Checking for mixed port assignment before swap conditions")
        port_assignment = handle_mixed_port_assignment(pin_display_name, value, df)
        if port_assignment:
            print(f"Step 3A: Mixed port assignment returned: {port_assignment}")
            return port_assignment
        
        # 3B. THEN: Check swap conditions
        for alt_name, priority in mappings['swap_conditions'].items():
            pin_names = str(value_alternative).split('/')
            if alt_name in pin_names:
                print(f"EXACT MATCH FOUND! '{alt_name}' found in '{value_alternative}' with priority {priority}")
                swap_pins_for_that_row(df, index, mappings['swap_conditions'])
                return priority
        
        #print(f"Step 3: No swap conditions met, returning P_{value}")
        return f"P_{value}"
  
    # 4B. Generic Port handling 
    generic_port_condition = value.strip().startswith("Port")
    #print(f"Step 4B: Generic port condition: {generic_port_condition}")
    
    if generic_port_condition:
        try:
            port_number = int(value.split(' ')[1])
            result = f"P_Port {port_number:02d}"
            #print(f"Step 4B: Generic port handling - returning {result}")
            return result
        except ValueError:
            result = f"P_Port {value.split(' ')[1]}"
            #print(f"Step 4B: Generic port handling (ValueError) - returning {result}")
            return result
    
    # 5. Default case
    #print("Step 5: Returning None (default case)")
    return None

'''def swap_pins_for_that_row(df, index, swap_conditions):
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
'''
        

def swap_pins_for_that_row(df, index, swap_conditions):
    current_display = df.loc[index, 'Pin Display Name']
    current_alternate = df.loc[index, 'Pin Alternate Name']
    
    # Find which swap_condition key is present in the alternate name as a separate pin
    for key in swap_conditions.keys():
        # Split by '/' to get individual pin names and check if key matches exactly
        pin_names = current_alternate.split('/')
        if key in pin_names:
            # Extract the matching part (e.g., "X1" from "P121/X1/INTP1")
            matched_part = key
            
            # Swap ONLY the matched part with display name
            new_alternate = current_alternate.replace(matched_part, current_display)
            new_display = matched_part
            
            df.loc[index, 'Pin Display Name'] = new_display
            df.loc[index, 'Pin Alternate Name'] = new_alternate
            
            # Update Electrical Type based on matched part
            if matched_part in ["X1", "X2", "XT1", "XT2", "MD", "NMI", "//RESET", "RESET"]:
                df.loc[index, 'Electrical Type'] = 'Input'
            elif matched_part == "RESOUT":
                df.loc[index, 'Electrical Type'] = 'Output'
            elif matched_part in ["VREF", "VRFF"]:
                df.loc[index, 'Electrical Type'] = 'Power'
            # Else keep electrical type as it is (no change needed)
            
            return

def handle_mixed_port_assignment(pin_display_name, grouping_value, df):
    """
    Handles special case where a port group contains both PXX and PXXX pins.
    Only shows debug output when mixed pins are found.
    """
    # Get all pins in the current group
    group_pins = df[df['Grouping'] == grouping_value]['Pin Display Name'].tolist()
    
    # Check if group has both PXX (3 chars) and PXXX (4 chars)
    has_pxx = any(len(pin) == 3 and pin.startswith('P') and pin[1:].isdigit() for pin in group_pins)
    has_pxxx = any(len(pin) == 4 and pin.startswith('P') and pin[1:].isdigit() for pin in group_pins)
    
    if has_pxx and has_pxxx:
        print(f"\n=== MIXED PORT GROUP DETECTED ===")
        print(f"Group: {grouping_value}")
        print(f"All pins: {group_pins}")
        print(f"Current pin: {pin_display_name}")
        
        pin = pin_display_name
        if len(pin) == 3 and pin.startswith('P'):  # PXX case
            port_num = int(pin[1])  # Take first digit after P
            print(f"Assigning {pin} to P_Port {port_num:02d} (PXX rule: first digit)")
            return f"P_Port {port_num:02d}"
        elif len(pin) == 4 and pin.startswith('P'):  # PXXX case
            port_num = int(pin[1:3])  # Take first two digits after P
            print(f"Assigning {pin} to P_Port {port_num:02d} (PXXX rule: first two digits)")
            return f"P_Port {port_num:02d}"
    
    return None
        
#######################################################


def assigning_side_for_priority(df):
    df_copy = df.copy()
    df_new = filter_and_sort_by_priority(df_copy)

    # Assign side
    df_new['Side'] = df_new.apply(lambda row: allocate_pin_side_by_priority(row, df_new), axis=1)
    print_grid_spaces(df_new)
    df_new = balance_grid_space(df_new)

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
    # print(f"\nPin Distribution:")
    # print(f"Total pins: {total_rows}")
    # print(f"Left side: {len(left)} pins")
    # print(f"Right side: {len(right)} pins")

    return 'Left' if row.name in left else 'Right'

def extract_numeric_key(pin_name):
    """Extract numeric part from pin name for sorting."""
    if '_' in pin_name:
        parts = pin_name.split('_')
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return 999999
    
    match = re.match(r'^([A-Za-z]+)(\d+)$', pin_name)
    if match:
        return int(match.group(2))
    
    return 999999

def assigning_ascending_order_for_similar_group(df, column_name='Pin Display Name'):
    """
    CORRECTED VERSION: Sort by Priority, then by numeric part of pin name.
    This replaces your existing function completely.
    """
    df = df.copy()
    
    # Extract numeric sorting key
    df['__numeric_key__'] = df[column_name].apply(extract_numeric_key)
    
    # Sort by Priority first, then by numeric key, then by pin name
    sorted_df = df.sort_values(
        by=['Priority', '__numeric_key__', column_name],
        ascending=[True, True, True]
    ).drop(columns=['__numeric_key__'])
    
    return sorted_df.reset_index(drop=True)

# Your existing assigning_side_for_less_than_80_pin_count function 
# should now work correctly with this replacement

def assigning_side_for_less_than_80_pin_count(df):
    df_Part = filter_and_sort_by_priority(df)
    df_Part['Side'] = df_Part.apply(lambda row: allocate_pin_side_by_priority(row, df_Part), axis=1)

    print_grid_spaces(df_Part)
    df_Part = balance_grid_space(df_Part)
    df_Part = assigning_ascending_order_for_similar_group(df_Part)  # Now uses corrected function

    return df_Part.reset_index(drop=True)

def print_grid_spaces(df):
    # Group pins by Priority
    grouped = df.groupby('Priority')

    # Determine side assignment for each pin using `allocate_pin_side_by_priority`
    df['Side'] = df.apply(lambda row: allocate_pin_side_by_priority(row, df), axis=1)

    # Initialize counters for grid usage
    left_grids = 0
    right_grids = 0

    print("\nGrid Usage:")
    for priority, group in grouped:
        pins_in_group = len(group)
        side = group['Side'].iloc[0]  # All pins in group are on the same side

        # Each pin takes one grid + 1 separator between groups
        if side == 'Left':
            left_grids += pins_in_group
            if left_grids != pins_in_group:  # Avoid separator before first group
                left_grids += 1
        else:
            right_grids += pins_in_group
            if right_grids != pins_in_group:
                right_grids += 1

        print(f"Group '{priority}' -> {pins_in_group} pins -> Side: {side}")

    print(f"\nTotal Grid Spaces:")
    print(f"Left: {left_grids} grids")
    print(f"Right: {right_grids} grids")
    print(f"Unused grids : {abs(left_grids - right_grids)}")


def balance_grid_space(df):
    print("\n=== DEBUG: Starting Revised balance_grid_space() ===")
    
    # Get group sizes and sides
    group_sizes = df.groupby('Priority').size()
    group_sides = df.groupby('Priority')['Side'].first()
    
    print("\nInitial Side Assignments:")
    print(group_sides)
    
    # Find the last left group and first right group
    left_groups = group_sides[group_sides == 'Left'].index.tolist()
    right_groups = group_sides[group_sides == 'Right'].index.tolist()
    
    if not left_groups or not right_groups:
        return df  # No balancing needed
    
    last_left = left_groups[-1]
    first_right = right_groups[0]
    
    print(f"\nTransition Boundary: Last Left = {last_left}, First Right = {first_right}")
    
    # Current grid usage (rows + separators)
    left_grids = sum(group_sizes[group_sides == 'Left']) + max(0, len(left_groups) - 1)
    right_grids = sum(group_sizes[group_sides == 'Right']) + max(0, len(right_groups) - 1)
    imbalance = abs(left_grids - right_grids)
    
    print(f"\nCurrent Grid Usage: Left={left_grids}, Right={right_grids} (Imbalance: {imbalance})")
    
    if imbalance <= 1:
        print("\nImbalance <= 1. No action taken.")
        return df

    size_last_left = group_sizes[last_left]
    size_first_right = group_sizes[first_right]

    # Simulate moving last_left to Right
    new_left_grids_LtoR = left_grids - size_last_left - (1 if len(left_groups) > 1 else 0)
    new_right_grids_LtoR = right_grids + size_last_left + (1 if len(right_groups) > 0 else 0)
    new_imbalance_LtoR = abs(new_left_grids_LtoR - new_right_grids_LtoR)

    print(f"\nHypothetical Swap: Move {last_left} (Size={size_last_left}) to Right")
    print(f"  → New Left Grids: {new_left_grids_LtoR}, New Right Grids: {new_right_grids_LtoR} (Imbalance: {new_imbalance_LtoR})")

    # Simulate moving first_right to Left
    new_left_grids_RtoL = left_grids + size_first_right + (1 if len(left_groups) > 0 else 0)
    new_right_grids_RtoL = right_grids - size_first_right - (1 if len(right_groups) > 1 else 0)
    new_imbalance_RtoL = abs(new_left_grids_RtoL - new_right_grids_RtoL)

    print(f"\nHypothetical Swap: Move {first_right} (Size={size_first_right}) to Left")
    print(f"  → New Left Grids: {new_left_grids_RtoL}, New Right Grids: {new_right_grids_RtoL} (Imbalance: {new_imbalance_RtoL})")

    # Choose the better move
    if new_imbalance_LtoR < imbalance or new_imbalance_RtoL < imbalance:
        if new_imbalance_RtoL <= new_imbalance_LtoR:
            print(f"  ✅ Swap APPROVED: Move {first_right} to Left (New Imbalance: {new_imbalance_RtoL})")
            df.loc[df['Priority'] == first_right, 'Side'] = 'Left'
        else:
            print(f"  ✅ Swap APPROVED: Move {last_left} to Right (New Imbalance: {new_imbalance_LtoR})")
            df.loc[df['Priority'] == last_left, 'Side'] = 'Right'
    else:
        print("  ❌ No swap improves the imbalance. No action taken.")
    
    print("\n=== DEBUG: Ending balance_grid_space() ===")
    return df


##########################################


'''def assigning_side_for_priority_for_dataframes_within_dictionary(dfs):
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
    
    return final_dfs'''

def assigning_side_for_priority_for_dataframes_within_dictionary(dfs):
    final_dfs = {}
    table_keys = list(dfs.keys())

    for idx, (title, df) in enumerate(dfs.items()):
        df_copy = df.copy()
        # Apply the side assignment logic to the DataFrame
        df_new = assigning_side_for_less_than_80_pin_count(df_copy)
        
        # (Other logic may go here...)

        # Store final result for this part
        final_dfs[title] = df_new

    return final_dfs



def assigning_side_for_less_than_80_pin_count(df):
    if df.empty:
        print("Warning: Empty DataFrame passed to assigning_side_for_less_than_80_pin_count")
        return df
    df_Part = filter_and_sort_by_priority(df)
    df_Part['Side'] = df_Part.apply(lambda row: allocate_pin_side_by_priority(row, df_Part), axis=1)

    print_grid_spaces(df_Part)
    df_Part = balance_grid_space(df_Part)
    df_Part = assigning_ascending_order_for_similar_group(df_Part)

    return df_Part.reset_index(drop=True)

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

    # Step 4: Convert 'Pin Designator' to int if possible BEFORE string cleanup
    if "Pin Designator" in df.columns:
        df["Pin Designator"] = df["Pin Designator"].apply(
            lambda x: int(float(x)) if isinstance(x, (int, float)) or 
                      (isinstance(x, str) and x.replace('.', '', 1).isdigit()) 
                      else x
        )

    # Step 5: Clean string values only in object/string columns
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(lambda x: str(x).strip().replace('  ', ' ')
                                .replace('\n', ' ').replace(' ', '_'))

    return df


#############################################

def partitioning(df_last, Strict_Population):
    # Step 1: Filter and sort by priority
    df = filter_and_sort_by_priority(df_last)

    # Step 2: Apply filter for power pins and update the 'Side' column
    df['Side'] = df.apply(filter_out_power_pins, args=(df,), axis=1)
    power_df = df[df['Side'].isin(['Left', 'Right'])]
    df.loc[power_df.index, 'Side'] = power_df['Side']

    print("Power DataFrame:", power_df)

    # Step 3: Handle unfilled rows
    unfilled_df = df[df['Side'].isna()]
    number_of_rows_left = len(unfilled_df)
    print(f"Length of unfilled DataFrame: {number_of_rows_left}")

    # Initialize result DataFrames
    df_Part_A = pd.DataFrame()
    port_df_side_added = pd.DataFrame()
    Port_Balance_1 = pd.DataFrame()
    Port_Balance_2 = pd.DataFrame()
    Port_Part_1 = pd.DataFrame()
    gpio_1 = pd.DataFrame()
    gpio_2 = pd.DataFrame()
    gpio_3 = pd.DataFrame()

    # Handle cases based on the number of unfilled rows
    if number_of_rows_left <= 80:
        print("Only one extra Part")

        df_Part_A = filter_and_sort_by_priority(unfilled_df)
        df_Part_A['Side'] = df_Part_A.apply(lambda row: allocate_pin_side_by_priority(row, df_Part_A), axis=1)
        print_grid_spaces(df_Part_A)
        df_Part_A = balance_grid_space(df_Part_A)

        # Update unfilled rows in the original DataFrame
        df.loc[unfilled_df.index, 'Side'] = df_Part_A['Side'].values

        # Recheck unfilled rows
        number_of_rows_left = df['Side'].isna().sum()
        print(f"Length of unfilled DataFrame: {number_of_rows_left}")

        if number_of_rows_left == 0:
            print("All bins are filled. Initializing empty DataFrames.")
        else:
            print("Something is wrong")
            print(f"Unfilled DataFrame: {df[df['Side'].isna()]}")
    
    elif number_of_rows_left > 80 and any(unfilled_df['Priority'].str.startswith('P_Port')):
        port_df = unfilled_df[unfilled_df['Priority'].str.startswith('P_Port')]
        other_unnamed_df = unfilled_df[~unfilled_df.index.isin(port_df.index)]

        print(f"Port df length: {len(port_df)}")
        print(f"Other unnamed df length: {len(other_unnamed_df)}")
        
        combined_df = pd.concat([port_df, other_unnamed_df], ignore_index=True)
        overall_length = len(combined_df)
        print(f"Overall length of combined DataFrame: {overall_length}")

        ''' if len(port_df) < 80:
            port_df_side_added = assigning_side_for_less_than_80_pin_count(port_df)
            df.loc[port_df.index, 'Side'] = port_df_side_added['Side'].values
        elif 80 < len(combined_df) <= 160:
            # Split into Port_Part_1 and Port_Balance_1
            Port_Part_1, Port_Balance_1 = split_into_parts(combined_df, max_rows=80)
        else:
            # Split into three parts
            Port_Part_1, Port_Balance_1, Port_Balance_2 = split_into_three_parts(combined_df, max_rows=80) 
            '''
        
        if len(port_df) < 80:
            port_df_side_added = assigning_side_for_less_than_80_pin_count(port_df)
            df.loc[port_df.index, 'Side'] = port_df_side_added['Side'].values
            
        else:
            # Calculate number of parts needed
            n_parts_needed = (len(combined_df) + 79) // 80  # Ceiling division
            port_parts = split_into_n_parts(combined_df, n_parts_needed, max_rows=80,Strict_Population=Strict_Population)
            
            # Assign to variables for backward compatibility
            Port_Part_1 = port_parts[0] if len(port_parts) > 0 else pd.DataFrame()
            Port_Balance_1 = port_parts[1] if len(port_parts) > 1 else pd.DataFrame()
            Port_Balance_2 = port_parts[2] if len(port_parts) > 2 else pd.DataFrame()
            
            # Store additional parts if any
            additional_port_parts = port_parts[3:] if len(port_parts) > 3 else []
            

    
    else:
        print("You will have to create more Parts")
        # Run Case 1 inside else
        gpio_parts = test_one_GPIOcase(unfilled_df, df)
        
        # Assign to variables for backward compatibility
        gpio_1 = gpio_parts[0] if len(gpio_parts) > 0 else pd.DataFrame()
        gpio_2 = gpio_parts[1] if len(gpio_parts) > 1 else pd.DataFrame()
        gpio_3 = gpio_parts[2] if len(gpio_parts) > 2 else pd.DataFrame()
        
        # Store additional GPIO parts if any
        additional_gpio_parts = gpio_parts[3:] if len(gpio_parts) > 3 else []

    
    # Step 4: Construct the dictionary of DataFrames
    df_dict = {
        'Power Table': power_df,
        'Part A Table': df_Part_A,
        'Port Table': port_df_side_added,
        'Others Table': df[df['Side'].isna()],
        'Port Table - 1': Port_Part_1,
        'Port Table - 2': Port_Balance_1,
        'Port Table - 3': Port_Balance_2,
    }

    # Add additional port parts dynamically
    if 'additional_port_parts' in locals():
        for i, part in enumerate(additional_port_parts, start=4):
            if not part.empty:
                df_dict[f'Port Table - {i}'] = part

    # Add additional GPIO parts dynamically
    if 'additional_gpio_parts' in locals():
        for i, part in enumerate(additional_gpio_parts, start=4):
            if not part.empty:
                df_dict[f'GPIO Table - {i}'] = part



    # Clean up the dictionary by removing empty DataFrames
    df_dict = {key: value for key, value in df_dict.items() if not value.empty}

    # DEDUPLICATION: Remove duplicates from Others Table
    df_dict = remove_duplicates_from_others_table(df_dict)

    # Final validation of splitting logic
    total_rows_processed = sum(len(table) for table in df_dict.values())
    if total_rows_processed != len(df):
        print("❗Something went wrong with splitting into parts.")
        print(f"🧮 Total rows processed: {total_rows_processed}, Original rows: {len(df)}")

    return df_dict


def split_into_n_parts(df, n_parts, max_rows=80, Strict_Population= True):
    # Step 1: Sort groups by numeric key to ensure ordered processing
    grouped_indices = {
        k: v for k, v in sorted(
            df.groupby('Priority').indices.items(),
            key=lambda item: extract_numeric_key(item[0])
        )
    }

    parts = [pd.DataFrame() for _ in range(n_parts)]
    part_row_counts = [0] * n_parts

    if Strict_Population:
        # Original behavior (first part with space)
        for priority, indices in grouped_indices.items():
            group = df.loc[indices]
            for i in range(n_parts):
                if part_row_counts[i] + len(group) <= max_rows:
                    parts[i] = pd.concat([parts[i], group], ignore_index=True)
                    part_row_counts[i] += len(group)
                    break
            else:
                # Force append to last part if no room
                parts[-1] = pd.concat([parts[-1], group], ignore_index=True)
    else:
        # Strict ordered part population
        current_part = 0
        for priority, indices in grouped_indices.items():
            group = df.loc[indices]

            if part_row_counts[current_part] + len(group) > max_rows:
                current_part += 1
                if current_part >= n_parts:
                    print(f"⚠️ Not enough parts to hold all groups within max_rows limit.")
                    break

            parts[current_part] = pd.concat([parts[current_part], group], ignore_index=True)
            part_row_counts[current_part] += len(group)

    return parts



def remove_duplicates_from_others_table(df_dict):
    """
    Remove any rows from 'Others Table' that appear in any other table
    """
    if 'Others Table' not in df_dict or df_dict['Others Table'].empty:
        return df_dict
    
    others_df = df_dict['Others Table'].copy()
    
    # Get all other tables (exclude 'Others Table')
    other_tables = {key: df for key, df in df_dict.items() if key != 'Others Table' and not df.empty}
    
    if not other_tables:
        return df_dict
    
    # Combine all other tables to find duplicates
    all_other_rows = pd.concat(other_tables.values(), ignore_index=True)
    
    # Find rows in Others Table that don't exist in other tables
    # Using a combination of key columns to identify unique rows
    key_columns = ['Pin Display Name', 'Pin Designator']  # Adjust these columns as needed
    
    # Create a set of tuples for fast lookup
    other_rows_set = set()
    for _, row in all_other_rows.iterrows():
        key_tuple = tuple(row[col] for col in key_columns if col in row.index)
        other_rows_set.add(key_tuple)
    
    # Filter Others Table to remove duplicates
    filtered_others = []
    for _, row in others_df.iterrows():
        key_tuple = tuple(row[col] for col in key_columns if col in row.index)
        if key_tuple not in other_rows_set:
            filtered_others.append(row)
    
    # Update the Others Table
    if filtered_others:
        df_dict['Others Table'] = pd.DataFrame(filtered_others).reset_index(drop=True)
    else:
        # Remove Others Table if it's empty after deduplication
        df_dict.pop('Others Table', None)
    
    return df_dict

def filter_out_power_pins(row, df):
    """
    FIXED VERSION: Better handling of NaN values and side assignment
    """
    # Fill NaN values in Priority column
    priority_value = str(row['Priority']) if pd.notna(row['Priority']) else ''

    # Check for left power pins (starting with 'A')
    if priority_value.startswith('A'):
        return 'Left'
    # Check for right power pins (starting with 'Z' or 'Y')  
    elif priority_value.startswith(('Z', 'Y')):
        return 'Right'
    else:
        return None
    

def test_one_GPIOcase(unfilled_df, df):
    print("Test One - Seeing if there are more pins that are GPIO")

    gpio_mask = unfilled_df['Priority'].str.contains('GPIO_Pins', na=False)
    gpio_df = unfilled_df[gpio_mask]

    if gpio_df.empty:
        print("No GPIO Pins found — passing for now.")
        return []

    gpio_count = len(gpio_df)
    print(f"Found {gpio_count} GPIO Pins")

    other_unnamed_df = unfilled_df[~unfilled_df.index.isin(gpio_df.index)]        
    combined_df = pd.concat([gpio_df, other_unnamed_df], ignore_index=True)

    if 40 < len(gpio_df) < 80:
        port_df_side_added = assigning_side_for_less_than_80_pin_count(gpio_df)
        df.loc[gpio_df.index, 'Side'] = port_df_side_added['Side'].values
        return [port_df_side_added]

    else:
        # Calculate number of parts needed
        n_parts_needed = (len(combined_df) + 79) // 80  # Ceiling division
        gpio_parts = split_into_n_parts(combined_df, n_parts_needed, max_rows=80,Strict_Population=True)
        return gpio_parts




###########################################

