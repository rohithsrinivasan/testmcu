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

'''def balance_grid_space(df):
    print("\n=== DEBUG: Starting Revised balance_grid_space() ===")
    
    # Get group sizes and side assignments
    group_sizes = df.groupby('Priority').size()
    group_sides = df.groupby('Priority')['Side'].first()
    
    print("\nInitial Side Assignments:")
    print(group_sides)
    
    left_groups = group_sides[group_sides == 'Left'].index.tolist()
    right_groups = group_sides[group_sides == 'Right'].index.tolist()
    
    # Handle case where all groups are on one side
    if not left_groups or not right_groups:
        dominant_side = 'Left' if left_groups else 'Right'
        print(f"\n⚠️  All groups are on one side ({dominant_side}). Balancing across sides...")
        
        all_groups = group_sides.index.tolist()
        
        # Special case: Only one group exists
        if len(all_groups) == 1:
            single_group = all_groups[0]
            group_df = df[df['Priority'] == single_group]
            total_pins = len(group_df)

            print(f"  → Only one group '{single_group}' with {total_pins} pins. Sorting and splitting...")

            if total_pins >= 2:
                # Sort pins in ascending order
                group_df_sorted = assigning_ascending_order_for_similar_group(group_df, column_name='Pin Display Name')

                # Split pins in half
                half = total_pins // 2
                left_indices = group_df_sorted.iloc[:half].index
                right_indices = group_df_sorted.iloc[half:].index

                # Assign sides directly
                df.loc[left_indices, 'Side'] = 'Left'
                df.loc[right_indices, 'Side'] = 'Right'

                print(f"  → Split: {half} pins to Left, {total_pins - half} pins to Right")
            else:
                print(f"  → Only {total_pins} pin(s) in group. Cannot split further.")
                return df
        else:
            # Multiple groups - reassign half to opposite side
            half = len(all_groups) // 2
            new_left = all_groups[:half]
            new_right = all_groups[half:]
            print(f"  → Moving {len(new_left)} groups to Left, {len(new_right)} groups to Right")
            df.loc[df['Priority'].isin(new_left), 'Side'] = 'Left'
            df.loc[df['Priority'].isin(new_right), 'Side'] = 'Right'

        # Recompute after balancing
        group_sizes = df.groupby('Priority').size()
        group_sides = df.groupby('Priority')['Side'].first()
        left_groups = group_sides[group_sides == 'Left'].index.tolist()
        right_groups = group_sides[group_sides == 'Right'].index.tolist()

        print(f"\nAfter balancing - Left groups: {left_groups}, Right groups: {right_groups}")
    
    # Check if we still have groups on both sides for normal balancing logic
    if not left_groups or not right_groups:
        print("\nAfter initial balancing, still no groups on one side. Skipping further balancing.")
        return df
    
    # Now apply normal balancing logic
    last_left = left_groups[-1]
    first_right = right_groups[0]
    print(f"\nTransition Boundary: Last Left = {last_left}, First Right = {first_right}")
    
    left_grids = sum(group_sizes[group_sides == 'Left']) + max(0, len(left_groups) - 1)
    right_grids = sum(group_sizes[group_sides == 'Right']) + max(0, len(right_groups) - 1)
    imbalance = abs(left_grids - right_grids)
    
    print(f"\nCurrent Grid Usage: Left={left_grids}, Right={right_grids} (Imbalance: {imbalance})")
    
    if imbalance <= 1:
        print("\nImbalance <= 1. No action taken.")
        return df
    
    size_last_left = group_sizes[last_left]
    size_first_right = group_sizes[first_right]
    
    new_left_grids_LtoR = left_grids - size_last_left - (1 if len(left_groups) > 1 else 0)
    new_right_grids_LtoR = right_grids + size_last_left + (1 if len(right_groups) > 0 else 0)
    new_imbalance_LtoR = abs(new_left_grids_LtoR - new_right_grids_LtoR)
    print(f"\nHypothetical Swap: Move {last_left} (Size={size_last_left}) to Right")
    print(f"  → New Left Grids: {new_left_grids_LtoR}, New Right Grids: {new_right_grids_LtoR} (Imbalance: {new_imbalance_LtoR})")
    
    new_left_grids_RtoL = left_grids + size_first_right + (1 if len(left_groups) > 0 else 0)
    new_right_grids_RtoL = right_grids - size_first_right - (1 if len(right_groups) > 1 else 0)
    new_imbalance_RtoL = abs(new_left_grids_RtoL - new_right_grids_RtoL)
    print(f"\nHypothetical Swap: Move {first_right} (Size={size_first_right}) to Left")
    print(f"  → New Left Grids: {new_left_grids_RtoL}, New Right Grids: {new_right_grids_RtoL} (Imbalance: {new_imbalance_RtoL})")
    
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
    return df'''

def split_large_identical_groups(df, current_unused_grids):
    """
    Split large groups where all pins have identical names into smaller subgroups
    to minimize unused grids. Only called when unused grids > 30.
    """
    print(f"\n=== Splitting large groups to reduce unused grids ({current_unused_grids}) ===")
    
    # Create a copy to avoid modifying original during iteration
    df_modified = df.copy()
    
    # Find the largest group with identical pin names
    largest_group = None
    largest_size = 0
    largest_priority = None
    
    for priority, group in df.groupby('Priority'):
        group_size = len(group)
        unique_names = group['Pin Display Name'].nunique()
        
        if unique_names == 1 and group_size > largest_size:  # All pins have identical names
            largest_group = group
            largest_size = group_size
            largest_priority = priority
    
    if largest_group is None:
        print("No large groups with identical pin names found for splitting")
        return df_modified
    
    pin_name = largest_group['Pin Display Name'].iloc[0]
    print(f"Found largest group '{largest_priority}' with {largest_size} identical pins ('{pin_name}')")
    
    # Calculate current grid distribution
    group_sizes = df.groupby('Priority').size()
    group_sides = df.groupby('Priority')['Side'].first()
    
    left_groups = group_sides[group_sides == 'Left'].index.tolist()
    right_groups = group_sides[group_sides == 'Right'].index.tolist()
    
    current_left_grids = sum(group_sizes[group_sides == 'Left']) + max(0, len(left_groups) - 1)
    current_right_grids = sum(group_sizes[group_sides == 'Right']) + max(0, len(right_groups) - 1)
    
    print(f"Current: Left={current_left_grids}, Right={current_right_grids}, Unused={current_unused_grids}")
    
    # Try different split sizes to find the one that minimizes unused grids
    best_split = None
    best_unused_grids = current_unused_grids
    
    # Try splitting the largest group into 2 parts with different ratios
    for split_ratio in [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7]:
        group1_size = int(largest_size * split_ratio)
        group2_size = largest_size - group1_size
        
        if group1_size == 0 or group2_size == 0:
            continue
            
        # Calculate what happens if we put group1 on left and group2 on right
        # (or vice versa depending on which side the original group was on)
        original_side = group_sides[largest_priority]
        
        if original_side == 'Left':
            # Remove original group from left, add split groups to both sides
            new_left_grids = current_left_grids - largest_size + group1_size
            new_right_grids = current_right_grids + group2_size + (1 if len(right_groups) > 0 else 0)
        else:
            # Remove original group from right, add split groups to both sides
            new_left_grids = current_left_grids + group1_size + (1 if len(left_groups) > 0 else 0)
            new_right_grids = current_right_grids - largest_size + group2_size
        
        new_unused_grids = abs(new_left_grids - new_right_grids)
        
        print(f"  Split ratio {split_ratio:.2f}: {group1_size}/{group2_size} pins → Unused grids: {new_unused_grids}")
        
        if new_unused_grids < best_unused_grids:
            best_unused_grids = new_unused_grids
            best_split = (group1_size, group2_size, split_ratio)
    
    if best_split is None:
        print("No beneficial split found")
        return df_modified
    
    group1_size, group2_size, split_ratio = best_split
    print(f"  → Best split: {group1_size} + {group2_size} pins (ratio {split_ratio:.2f})")
    print(f"  → Unused grids will reduce from {current_unused_grids} to {best_unused_grids}")
    
    # Apply the best split
    group_sorted = largest_group.sort_values('Pin Designator')
    
    # Split into two groups
    group1_indices = group_sorted.iloc[:group1_size].index
    group2_indices = group_sorted.iloc[group1_size:].index
    
    # Create new priority names
    new_priority1 = f"{largest_priority}_1"
    new_priority2 = f"{largest_priority}_2"
    
    # Update priorities
    df_modified.loc[group1_indices, 'Priority'] = new_priority1
    df_modified.loc[group2_indices, 'Priority'] = new_priority2
    
    # Assign sides to minimize unused grids
    original_side = group_sides[largest_priority]
    if original_side == 'Left':
        df_modified.loc[group1_indices, 'Side'] = 'Left'
        df_modified.loc[group2_indices, 'Side'] = 'Right'
    else:
        df_modified.loc[group1_indices, 'Side'] = 'Left'
        df_modified.loc[group2_indices, 'Side'] = 'Right'
    
    print(f"  → Created: '{new_priority1}' ({group1_size} pins) and '{new_priority2}' ({group2_size} pins)")
    
    return df_modified

def calculate_unused_grids(df):
    """
    Calculate current unused grids based on side assignments.
    """
    # Ensure side assignments exist
    if 'Side' not in df.columns:
        df['Side'] = df.apply(lambda row: allocate_pin_side_by_priority(row, df), axis=1)
    
    # Get group sizes and side assignments
    group_sizes = df.groupby('Priority').size()
    group_sides = df.groupby('Priority')['Side'].first()
    
    left_groups = group_sides[group_sides == 'Left'].index.tolist()
    right_groups = group_sides[group_sides == 'Right'].index.tolist()
    
    left_grids = sum(group_sizes[group_sides == 'Left']) + max(0, len(left_groups) - 1)
    right_grids = sum(group_sizes[group_sides == 'Right']) + max(0, len(right_groups) - 1)
    
    return abs(left_grids - right_grids)

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
    
    # Calculate initial unused grids to decide if splitting is needed
    initial_unused_grids = calculate_unused_grids(df)
    print(f"Initial unused grids: {initial_unused_grids}")
    
    # FIRST: Split large identical groups ONLY if unused grids > 30
    if initial_unused_grids > 30:
        print("Unused grids > 30, checking for large groups to split...")
        df = split_large_identical_groups(df, initial_unused_grids)
    else:
        print("Unused grids <= 30, skipping group splitting")
    
    # Get group sizes and side assignments
    group_sizes = df.groupby('Priority').size()
    group_sides = df.groupby('Priority')['Side'].first()
    
    print("\nSide Assignments after splitting:")
    print(group_sides)
    
    left_groups = group_sides[group_sides == 'Left'].index.tolist()
    right_groups = group_sides[group_sides == 'Right'].index.tolist()
    
    # Handle case where all groups are on one side
    if not left_groups or not right_groups:
        dominant_side = 'Left' if left_groups else 'Right'
        print(f"\n⚠️  All groups are on one side ({dominant_side}). Balancing across sides...")
        
        all_groups = group_sides.index.tolist()
        
        # Special case: Only one group exists
        if len(all_groups) == 1:
            single_group = all_groups[0]
            group_df = df[df['Priority'] == single_group]
            total_pins = len(group_df)
            print(f"\n🔍 DEBUG: Single group scenario")
            print(f"    Single group name: '{single_group}'")

            print(f"  → Only one group '{single_group}' with {total_pins} pins. Sorting and splitting...")

            if total_pins >= 2:
                # Sort pins in ascending order
                group_df_sorted = assigning_ascending_order_for_similar_group(group_df, column_name='Pin Display Name')

                # Split pins in half
                half = total_pins // 2
                left_indices = group_df_sorted.iloc[:half].index
                right_indices = group_df_sorted.iloc[half:].index

                # Assign sides directly
                df.loc[left_indices, 'Side'] = 'Left'
                df.loc[right_indices, 'Side'] = 'Right'

                print(f"  → Split: {half} pins to Left, {total_pins - half} pins to Right")
            else:
                print(f"  → Only {total_pins} pin(s) in group. Cannot split further.")
                return df
        else:
            # Multiple groups - reassign half to opposite side
            half = len(all_groups) // 2
            new_left = all_groups[:half]
            new_right = all_groups[half:]
            print(f"  → Moving {len(new_left)} groups to Left, {len(new_right)} groups to Right")
            df.loc[df['Priority'].isin(new_left), 'Side'] = 'Left'
            df.loc[df['Priority'].isin(new_right), 'Side'] = 'Right'

        # Recompute after balancing
        group_sizes = df.groupby('Priority').size()
        group_sides = df.groupby('Priority')['Side'].first()
        left_groups = group_sides[group_sides == 'Left'].index.tolist()
        right_groups = group_sides[group_sides == 'Right'].index.tolist()

        print(f"\nAfter balancing - Left groups: {left_groups}, Right groups: {right_groups}")
    
    # Check if we still have groups on both sides for normal balancing logic
    if not left_groups or not right_groups:
        print("\nAfter initial balancing, still no groups on one side. Skipping further balancing.")
        return df
    
    # Now apply normal balancing logic
    last_left = left_groups[-1]
    first_right = right_groups[0]
    print(f"\nTransition Boundary: Last Left = {last_left}, First Right = {first_right}")
    
    left_grids = sum(group_sizes[group_sides == 'Left']) + max(0, len(left_groups) - 1)
    right_grids = sum(group_sizes[group_sides == 'Right']) + max(0, len(right_groups) - 1)
    imbalance = abs(left_grids - right_grids)
    
    print(f"\nCurrent Grid Usage: Left={left_grids}, Right={right_grids} (Imbalance: {imbalance})")
    
    if imbalance <= 1:
        print("\nImbalance <= 1. No action taken.")
        return df
    
    size_last_left = group_sizes[last_left]
    size_first_right = group_sizes[first_right]
    
    new_left_grids_LtoR = left_grids - size_last_left - (1 if len(left_groups) > 1 else 0)
    new_right_grids_LtoR = right_grids + size_last_left + (1 if len(right_groups) > 0 else 0)
    new_imbalance_LtoR = abs(new_left_grids_LtoR - new_right_grids_LtoR)
    print(f"\nHypothetical Swap: Move {last_left} (Size={size_last_left}) to Right")
    print(f"  → New Left Grids: {new_left_grids_LtoR}, New Right Grids: {new_right_grids_LtoR} (Imbalance: {new_imbalance_LtoR})")
    
    new_left_grids_RtoL = left_grids + size_first_right + (1 if len(left_groups) > 0 else 0)
    new_right_grids_RtoL = right_grids - size_first_right - (1 if len(right_groups) > 1 else 0)
    new_imbalance_RtoL = abs(new_left_grids_RtoL - new_right_grids_RtoL)
    print(f"\nHypothetical Swap: Move {first_right} (Size={size_first_right}) to Left")
    print(f"  → New Left Grids: {new_left_grids_RtoL}, New Right Grids: {new_right_grids_RtoL} (Imbalance: {new_imbalance_RtoL})")
    
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

# Example usage:
# df_balanced = balance_grid_space(df)
# print_grid_spaces(df_balanced)


##########################################


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

'''def partitioning(df_last, Strict_Population):
    """
    Partitioning function with improved debugging and GPIO/SDRB separation
    Enhanced with power pin splitting capability
    """
    print("=== PARTITIONING START ===")
    
    # Step 1: Filter and sort by priority
    df = filter_and_sort_by_priority(df_last)
    print(f"Step 1: Filtered and sorted DataFrame - {len(df)} rows")

    # Step 2: Apply filter for power pins and update the 'Side' column
    df['Side'] = df.apply(filter_out_power_pins, args=(df,), axis=1)
    power_df = df[df['Side'].isin(['Left', 'Right'])]
    df.loc[power_df.index, 'Side'] = power_df['Side']
    print(f"Step 2: Power pins processed - {len(power_df)} power pins found")

    # NEW FEATURE: Handle power pin splitting if > 80 pins
    power_parts = []
    if len(power_df) > 80:
        print(f">>> Power pins > 80 ({len(power_df)}): Creating separate Power tables")
        power_parts = split_power_pins_by_priority(power_df, Strict_Population)
        print(f">>> Power separated: {len(power_parts)} Power parts created")
    else:
        # Keep original power_df if <= 80 pins
        if not power_df.empty:
            power_parts = [power_df]

    # Step 3: Handle unfilled rows
    unfilled_df = df[df['Side'].isna()]
    number_of_rows_left = len(unfilled_df)
    print(f"Step 3: Unfilled rows - {number_of_rows_left} rows remaining")

    # NEW FEATURE: Check for GPIO and SDRB pins that need separate handling
    gpio_pins = unfilled_df[unfilled_df['Priority'].str.contains('GPIO_Pins', na=False)]
    sdrb_pins = unfilled_df[unfilled_df['Priority'].str.contains('SDRB_Pins', na=False)]
    
    print(f"GPIO pins found: {len(gpio_pins)}")
    print(f"SDRB pins found: {len(sdrb_pins)}")
    
    # Separate GPIO/SDRB if they exceed 40 pins
    gpio_parts = []
    sdrb_parts = []
    
    if len(gpio_pins) > 40:
        print(">>> GPIO pins > 40: Creating separate GPIO tables")
        gpio_parts = test_one_GPIOcase(unfilled_df, df)
        # Remove GPIO pins from unfilled_df for main processing
        unfilled_df = unfilled_df[~unfilled_df['Priority'].str.contains('GPIO_Pins', na=False)]
        print(f">>> GPIO separated: {len(gpio_parts)} GPIO parts created")
    
    if len(sdrb_pins) > 40:
        print(">>> SDRB pins > 40: Creating separate SDRB tables")
        sdrb_parts = test_two_SRDBcase(unfilled_df, df)
        # Remove SDRB pins from unfilled_df for main processing
        unfilled_df = unfilled_df[~unfilled_df['Priority'].str.contains('SDRB_Pins', na=False)]
        print(f">>> SDRB separated: {len(sdrb_parts)} SDRB parts created")
    
    # Update the count after removing GPIO/SDRB
    number_of_rows_left = len(unfilled_df)
    print(f"Remaining unfilled rows after GPIO/SDRB separation: {number_of_rows_left}")

    # Initialize result DataFrames
    df_Part_A = pd.DataFrame()
    port_df_side_added = pd.DataFrame()
    Port_Balance_1 = pd.DataFrame()
    Port_Balance_2 = pd.DataFrame()
    Port_Part_1 = pd.DataFrame()
    additional_port_parts = []

    # MAIN LOGIC: Handle remaining unfilled rows (same as your original working logic)
    if number_of_rows_left <= 80:
        print(">>> CASE 1: Only one extra Part (≤80 rows)")
        
        df_Part_A = filter_and_sort_by_priority(unfilled_df)
        df_Part_A['Side'] = df_Part_A.apply(lambda row: allocate_pin_side_by_priority(row, df_Part_A), axis=1)
        print_grid_spaces(df_Part_A)
        df_Part_A = balance_grid_space(df_Part_A)

        # Update unfilled rows in the original DataFrame
        df.loc[unfilled_df.index, 'Side'] = df_Part_A['Side'].values

        # Recheck unfilled rows
        number_of_rows_left = df['Side'].isna().sum()
        print(f"After Part A processing: {number_of_rows_left} unfilled rows")

        if number_of_rows_left == 0:
            print("✅ All bins are filled.")
        else:
            print("❌ Something is wrong")
            print(f"Unfilled DataFrame: {df[df['Side'].isna()]}")
    
    elif number_of_rows_left > 80 and any(unfilled_df['Priority'].str.startswith('P_Port')):
        print(">>> CASE 2: Port-based splitting (>80 rows with P_Port)")
        
        port_df = unfilled_df[unfilled_df['Priority'].str.startswith('P_Port')]
        other_unnamed_df = unfilled_df[~unfilled_df.index.isin(port_df.index)]

        print(f"Port df length: {len(port_df)}")
        print(f"Other unnamed df length: {len(other_unnamed_df)}")
        
        combined_df = pd.concat([port_df, other_unnamed_df], ignore_index=True)
        overall_length = len(combined_df)
        print(f"Overall length of combined DataFrame: {overall_length}")
        
        if len(port_df) < 80:
            print(">>> Port pins < 80: Single port table")
            port_df_side_added = assigning_side_for_less_than_80_pin_count(port_df)
            df.loc[port_df.index, 'Side'] = port_df_side_added['Side'].values
        else:
            print(">>> Port pins ≥ 80: Multiple port tables")
            # Calculate number of parts needed
            n_parts_needed = (len(combined_df) + 79) // 80  # Ceiling division
            print(f"Creating {n_parts_needed} port parts")
            
            port_parts = split_into_n_parts(combined_df, n_parts_needed, max_rows=80, Strict_Population=Strict_Population)
            
            # Assign to variables for backward compatibility
            Port_Part_1 = port_parts[0] if len(port_parts) > 0 else pd.DataFrame()
            Port_Balance_1 = port_parts[1] if len(port_parts) > 1 else pd.DataFrame()
            Port_Balance_2 = port_parts[2] if len(port_parts) > 2 else pd.DataFrame()
            
            # Store additional parts if any
            additional_port_parts = port_parts[3:] if len(port_parts) > 3 else []
            print(f"Port parts created: Main={len(Port_Part_1)}, Balance1={len(Port_Balance_1)}, Balance2={len(Port_Balance_2)}, Additional={len(additional_port_parts)}")
    
    else:
        print(">>> CASE 3: Other cases - creating more parts")
        # Handle any remaining GPIO/SDRB that wasn't caught above
        if len(gpio_pins) <= 40 and len(gpio_pins) > 0:
            print(">>> Processing remaining GPIO pins (≤40)")
            gpio_parts = test_one_GPIOcase(unfilled_df, df)
        
        if len(sdrb_pins) <= 40 and len(sdrb_pins) > 0:
            print(">>> Processing remaining SDRB pins (≤40)")
            sdrb_parts = test_two_SRDBcase(unfilled_df, df)

    # Step 4: Construct the dictionary of DataFrames
    print("=== BUILDING RESULT DICTIONARY ===")
    
    df_dict = {
        'Part A Table': df_Part_A,
        'Port Table': port_df_side_added,
        'Others Table': df[df['Side'].isna()],
        'Port Table - 1': Port_Part_1,
        'Port Table - 2': Port_Balance_1,
        'Port Table - 3': Port_Balance_2,
    }

    # Add Power tables dynamically (UPDATED LOGIC)
    for i, part in enumerate(power_parts, start=1):
        if not part.empty:
            if len(power_parts) == 1:
                # Single power table (original behavior for <= 80 pins)
                df_dict['Power Table'] = part
                print(f"Added Power Table: {len(part)} rows")
            else:
                # Multiple power tables (new behavior for > 80 pins)
                df_dict[f'Power Table - {i}'] = part
                print(f"Added Power Table - {i}: {len(part)} rows")

    # Add additional port parts dynamically
    for i, part in enumerate(additional_port_parts, start=4):
        if not part.empty:
            df_dict[f'Port Table - {i}'] = part
            print(f"Added Port Table - {i}: {len(part)} rows")

    # Add GPIO tables dynamically
    for i, part in enumerate(gpio_parts, start=1):
        if not part.empty:
            df_dict[f'GPIO Table - {i}'] = part
            print(f"Added GPIO Table - {i}: {len(part)} rows")

    # Add SDRB tables dynamically  
    for i, part in enumerate(sdrb_parts, start=1):
        if not part.empty:
            df_dict[f'SDRB Table - {i}'] = part
            print(f"Added SDRB Table - {i}: {len(part)} rows")

    # Clean up the dictionary by removing empty DataFrames
    df_dict = {key: value for key, value in df_dict.items() if not value.empty}
    print(f"Final dictionary has {len(df_dict)} non-empty tables")

    # DEDUPLICATION: Remove duplicates from Others Table
    df_dict = remove_duplicates_from_others_table(df_dict)

    # Final validation of splitting logic
    total_rows_processed = sum(len(table) for table in df_dict.values())
    print(f"=== VALIDATION ===")
    print(f"Original rows: {len(df)}")
    print(f"Total rows processed: {total_rows_processed}")
    
    if total_rows_processed != len(df):
        print("❗ WARNING: Row count mismatch!")
        print("Table breakdown:")
        for key, table in df_dict.items():
            print(f"  {key}: {len(table)} rows")
    else:
        print("✅ All rows processed correctly")

    print("=== PARTITIONING END ===")
    return df_dict'''


def partitioning(df_last, Strict_Population):
    """
    Partitioning function with improved debugging and GPIO/SDRB separation
    Enhanced with power pin splitting capability and Others Table splitting
    """
    print("=== PARTITIONING START ===")
    
    # Step 1: Filter and sort by priority
    df = filter_and_sort_by_priority(df_last)
    print(f"Step 1: Filtered and sorted DataFrame - {len(df)} rows")

    # Step 2: Apply filter for power pins and update the 'Side' column
    df['Side'] = df.apply(filter_out_power_pins, args=(df,), axis=1)
    power_df = df[df['Side'].isin(['Left', 'Right'])]
    df.loc[power_df.index, 'Side'] = power_df['Side']
    print(f"Step 2: Power pins processed - {len(power_df)} power pins found")

    # NEW FEATURE: Handle power pin splitting if > 80 pins
    power_parts = []
    if len(power_df) > 80:
        print(f">>> Power pins > 80 ({len(power_df)}): Creating separate Power tables")
        power_parts = split_power_pins_by_priority(power_df, Strict_Population)
        print(f">>> Power separated: {len(power_parts)} Power parts created")
    else:
        # Keep original power_df if <= 80 pins
        if not power_df.empty:
            power_parts = [power_df]

    # Step 3: Handle unfilled rows
    unfilled_df = df[df['Side'].isna()]
    number_of_rows_left = len(unfilled_df)
    print(f"Step 3: Unfilled rows - {number_of_rows_left} rows remaining")

    # NEW FEATURE: Check for GPIO and SDRB pins that need separate handling
    gpio_pins = unfilled_df[unfilled_df['Priority'].str.contains('GPIO_Pins', na=False)]
    sdrb_pins = unfilled_df[unfilled_df['Priority'].str.contains('SDRB_Pins', na=False)]
    
    print(f"GPIO pins found: {len(gpio_pins)}")
    print(f"SDRB pins found: {len(sdrb_pins)}")
    
    # Separate GPIO/SDRB if they exceed 40 pins
    gpio_parts = []
    sdrb_parts = []
    
    if len(gpio_pins) > 40:
        print(">>> GPIO pins > 40: Creating separate GPIO tables")
        gpio_parts = test_one_GPIOcase(unfilled_df, df)
        # Remove GPIO pins from unfilled_df for main processing
        unfilled_df = unfilled_df[~unfilled_df['Priority'].str.contains('GPIO_Pins', na=False)]
        print(f">>> GPIO separated: {len(gpio_parts)} GPIO parts created")
    
    if len(sdrb_pins) > 40:
        print(">>> SDRB pins > 40: Creating separate SDRB tables")
        sdrb_parts = test_two_SRDBcase(unfilled_df, df)
        # Remove SDRB pins from unfilled_df for main processing
        unfilled_df = unfilled_df[~unfilled_df['Priority'].str.contains('SDRB_Pins', na=False)]
        print(f">>> SDRB separated: {len(sdrb_parts)} SDRB parts created")
    
    # Update the count after removing GPIO/SDRB
    number_of_rows_left = len(unfilled_df)
    print(f"Remaining unfilled rows after GPIO/SDRB separation: {number_of_rows_left}")

    # Initialize result DataFrames
    df_Part_A = pd.DataFrame()
    port_df_side_added = pd.DataFrame()
    Port_Balance_1 = pd.DataFrame()
    Port_Balance_2 = pd.DataFrame()
    Port_Part_1 = pd.DataFrame()
    additional_port_parts = []

    # MAIN LOGIC: Handle remaining unfilled rows (same as your original working logic)
    if number_of_rows_left <= 80:
        print(">>> CASE 1: Only one extra Part (≤80 rows)")
        
        df_Part_A = filter_and_sort_by_priority(unfilled_df)
        df_Part_A['Side'] = df_Part_A.apply(lambda row: allocate_pin_side_by_priority(row, df_Part_A), axis=1)
        print_grid_spaces(df_Part_A)
        df_Part_A = balance_grid_space(df_Part_A)

        # Update unfilled rows in the original DataFrame
        df.loc[unfilled_df.index, 'Side'] = df_Part_A['Side'].values

        # Recheck unfilled rows
        number_of_rows_left = df['Side'].isna().sum()
        print(f"After Part A processing: {number_of_rows_left} unfilled rows")

        if number_of_rows_left == 0:
            print("✅ All bins are filled.")
        else:
            print("❌ Something is wrong")
            print(f"Unfilled DataFrame: {df[df['Side'].isna()]}")
    
    elif number_of_rows_left > 80 and any(unfilled_df['Priority'].str.startswith('P_Port')):
        print(">>> CASE 2: Port-based splitting (>80 rows with P_Port)")
        
        port_df = unfilled_df[unfilled_df['Priority'].str.startswith('P_Port')]
        other_unnamed_df = unfilled_df[~unfilled_df.index.isin(port_df.index)]

        print(f"Port df length: {len(port_df)}")
        print(f"Other unnamed df length: {len(other_unnamed_df)}")
        
        combined_df = pd.concat([port_df, other_unnamed_df], ignore_index=True)
        overall_length = len(combined_df)
        print(f"Overall length of combined DataFrame: {overall_length}")
        
        if len(port_df) < 80:
            print(">>> Port pins < 80: Single port table")
            port_df_side_added = assigning_side_for_less_than_80_pin_count(port_df)
            df.loc[port_df.index, 'Side'] = port_df_side_added['Side'].values
        else:
            print(">>> Port pins ≥ 80: Multiple port tables")
            # Calculate number of parts needed
            n_parts_needed = (len(combined_df) + 79) // 80  # Ceiling division
            print(f"Creating {n_parts_needed} port parts")
            
            port_parts = split_into_n_parts(combined_df, n_parts_needed, max_rows=80, Strict_Population=Strict_Population)
            
            # Assign to variables for backward compatibility
            Port_Part_1 = port_parts[0] if len(port_parts) > 0 else pd.DataFrame()
            Port_Balance_1 = port_parts[1] if len(port_parts) > 1 else pd.DataFrame()
            Port_Balance_2 = port_parts[2] if len(port_parts) > 2 else pd.DataFrame()
            
            # Store additional parts if any
            additional_port_parts = port_parts[3:] if len(port_parts) > 3 else []
            print(f"Port parts created: Main={len(Port_Part_1)}, Balance1={len(Port_Balance_1)}, Balance2={len(Port_Balance_2)}, Additional={len(additional_port_parts)}")
    
    else:
        print(">>> CASE 3: Other cases - creating more parts")
        # Handle any remaining GPIO/SDRB that wasn't caught above
        if len(gpio_pins) <= 40 and len(gpio_pins) > 0:
            print(">>> Processing remaining GPIO pins (≤40)")
            gpio_parts = test_one_GPIOcase(unfilled_df, df)
        
        if len(sdrb_pins) <= 40 and len(sdrb_pins) > 0:
            print(">>> Processing remaining SDRB pins (≤40)")
            sdrb_parts = test_two_SRDBcase(unfilled_df, df)

    # Step 4: Construct the dictionary of DataFrames
    print("=== BUILDING RESULT DICTIONARY ===")
    
    df_dict = {
        'Part A Table': df_Part_A,
        'Port Table': port_df_side_added,
        'Others Table': df[df['Side'].isna()],
        'Port Table - 1': Port_Part_1,
        'Port Table - 2': Port_Balance_1,
        'Port Table - 3': Port_Balance_2,
    }

    # Add Power tables dynamically (UPDATED LOGIC)
    for i, part in enumerate(power_parts, start=1):
        if not part.empty:
            if len(power_parts) == 1:
                # Single power table (original behavior for <= 80 pins)
                df_dict['Power Table'] = part
                print(f"Added Power Table: {len(part)} rows")
            else:
                # Multiple power tables (new behavior for > 80 pins)
                df_dict[f'Power Table - {i}'] = part
                print(f"Added Power Table - {i}: {len(part)} rows")

    # Add additional port parts dynamically
    for i, part in enumerate(additional_port_parts, start=4):
        if not part.empty:
            df_dict[f'Port Table - {i}'] = part
            print(f"Added Port Table - {i}: {len(part)} rows")

    # Add GPIO tables dynamically
    for i, part in enumerate(gpio_parts, start=1):
        if not part.empty:
            df_dict[f'GPIO Table - {i}'] = part
            print(f"Added GPIO Table - {i}: {len(part)} rows")

    # Add SDRB tables dynamically  
    for i, part in enumerate(sdrb_parts, start=1):
        if not part.empty:
            df_dict[f'SDRB Table - {i}'] = part
            print(f"Added SDRB Table - {i}: {len(part)} rows")

    # Clean up the dictionary by removing empty DataFrames
    df_dict = {key: value for key, value in df_dict.items() if not value.empty}
    print(f"Final dictionary has {len(df_dict)} non-empty tables")

    # DEDUPLICATION: Remove duplicates from Others Table
    df_dict = remove_duplicates_from_others_table(df_dict)

    # NEW FEATURE: Handle Others Table splitting if > 80 pins
    others_parts = []
    if 'Others Table' in df_dict and len(df_dict['Others Table']) > 80:
        others_table = df_dict['Others Table']
        others_count = len(others_table)
        print(f"\n>>> Others Table > 80 pins ({others_count}): Splitting into multiple tables")
        
        # Calculate number of parts needed (max 80 per part)
        n_others_parts = (others_count + 79) // 80  # Ceiling division
        print(f">>> Creating {n_others_parts} Others Table parts")
        
        # Split the Others Table using the same strategy as port splitting
        others_parts = split_into_n_parts(others_table, n_others_parts, max_rows=80, Strict_Population=Strict_Population)
        
        # Remove the original Others Table from dict
        del df_dict['Others Table']
        
        # Add the split Others Tables
        for i, part in enumerate(others_parts, start=1):
            if not part.empty:
                df_dict[f'Others Table - {i}'] = part
                print(f"Added Others Table - {i}: {len(part)} rows")
        
        print(f">>> Others Table split complete: {len(others_parts)} parts created")

    # Final validation of splitting logic
    total_rows_processed = sum(len(table) for table in df_dict.values())
    print(f"=== VALIDATION ===")
    print(f"Original rows: {len(df)}")
    print(f"Total rows processed: {total_rows_processed}")
    
    if total_rows_processed != len(df):
        print("❗ WARNING: Row count mismatch!")
        print("Table breakdown:")
        for key, table in df_dict.items():
            print(f"  {key}: {len(table)} rows")
    else:
        print("✅ All rows processed correctly")

    print("=== PARTITIONING END ===")
    return df_dict


def split_power_pins_by_priority(power_df, Strict_Population, max_rows=80):
    """
    Split power pins into multiple DataFrames based on priority grouping constraints
    """

    print(f"\n=== SPLITTING POWER PINS ({len(power_df)} total) ===")

    if power_df.empty:
        print("  [DEBUG] Input power_df is empty. Returning empty list.")
        return []

    # Print initial column info and sample
    print(f"  [DEBUG] Input DataFrame columns: {power_df.columns.tolist()}")
    print(f"  [DEBUG] Sample rows:\n{power_df.head(3)}")

    # Sort by priority to maintain order
    power_df_sorted = power_df.sort_values('Priority', na_position='last').reset_index(drop=True)
    print(f"  [DEBUG] Sorted power_df by Priority. First 3 priorities: {power_df_sorted['Priority'].head(3).tolist()}")

    # Group pins by priority prefix
    priority_groups = {
        'A_group': power_df_sorted[power_df_sorted['Priority'].astype(str).str.startswith('A')],
        'Z_Y_group': power_df_sorted[power_df_sorted['Priority'].astype(str).str.startswith(('Z', 'Y'))],
        'Other_group': power_df_sorted[~power_df_sorted['Priority'].astype(str).str.startswith(('A', 'Z', 'Y'))]
    }

    print("Priority grouping:")
    for name, group in priority_groups.items():
        print(f"  [DEBUG] {name}: {len(group)} pins")

    power_parts = []

    # Process each group
    for group_name, group_df in priority_groups.items():
        if group_df.empty:
            print(f"  [DEBUG] Skipping {group_name} - empty group.")
            continue

        print(f"\nProcessing {group_name}: {len(group_df)} pins")

        if len(group_df) <= max_rows:
            print(f"  [DEBUG] Group fits within {max_rows} rows.")
            try:
                group_df_processed = assigning_side_for_less_than_80_pin_count(group_df)
                power_parts.append(group_df_processed)
                print(f"  -> Created single part with {len(group_df_processed)} pins")
            except Exception as e:
                print(f"  [ERROR] Failed to assign side for {group_name}: {e}")
        else:
            print(f"  [DEBUG] Group exceeds {max_rows} rows, needs splitting.")
            try:
                group_parts = split_large_power_group(group_df, max_rows)
                print(f"  [DEBUG] Split into {len(group_parts)} parts.")
                for idx, part in enumerate(group_parts):
                    print(f"    Part {idx + 1}: {len(part)} pins")
                power_parts.extend(group_parts)
            except Exception as e:
                print(f"  [ERROR] Failed to split {group_name}: {e}")

    # Final merge for small parts
    try:
        original_count = len(power_parts)
        power_parts = merge_small_power_parts(power_parts, max_rows)
        print(f"\n[DEBUG] Merged small power parts. Before: {original_count}, After: {len(power_parts)}")
    except Exception as e:
        print(f"  [ERROR] Failed during merging small parts: {e}")

    print(f"\nFinal power parts: {len(power_parts)} DataFrames")
    for i, part in enumerate(power_parts, 1):
        print(f"  Power part {i}: {len(part)} pins")

    return power_parts




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


def split_large_power_group(group_df, max_rows):
    """
    Split a large power group into multiple parts of max_rows each
    """
    parts = []
    
    for i in range(0, len(group_df), max_rows):
        part = group_df.iloc[i:i + max_rows].copy()
        part_processed = assigning_side_for_less_than_80_pin_count(part)
        parts.append(part_processed)
    
    return parts


def merge_small_power_parts(power_parts, max_rows):
    """
    Try to merge small power parts together to optimize DataFrame count
    while respecting the max_rows constraint
    """
    if len(power_parts) <= 1:
        return power_parts
    
    merged_parts = []
    current_merge = pd.DataFrame()
    
    for part in power_parts:
        # Check if we can merge this part with current_merge
        if len(current_merge) + len(part) <= max_rows:
            # Merge is possible
            if current_merge.empty:
                current_merge = part.copy()
            else:
                current_merge = pd.concat([current_merge, part], ignore_index=True)
        else:
            # Can't merge, finalize current_merge and start new one
            if not current_merge.empty:
                merged_parts.append(current_merge)
            current_merge = part.copy()
    
    # Add the last merge
    if not current_merge.empty:
        merged_parts.append(current_merge)
    
    return merged_parts


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
        gpio_parts = split_into_n_parts(combined_df, n_parts_needed, max_rows=80,Strict_Population=False)
        return gpio_parts
    

def test_two_SRDBcase(unfilled_df, df):
    """
    Handles SDRB_Pins from the Priority column - mirrors the GPIO logic
    """
    print("Test Two - Seeing if there are more pins that are SDRB")

    sdrb_mask = unfilled_df['Priority'].str.contains('SDRB_Pins', na=False)
    sdrb_df = unfilled_df[sdrb_mask]

    if sdrb_df.empty:
        print("No SDRB Pins found — passing for now.")
        return []

    sdrb_count = len(sdrb_df)
    print(f"Found {sdrb_count} SDRB Pins")

    other_unnamed_df = unfilled_df[~unfilled_df.index.isin(sdrb_df.index)]        
    combined_df = pd.concat([sdrb_df, other_unnamed_df], ignore_index=True)

    if 40 < len(sdrb_df) < 80:
        port_df_side_added = assigning_side_for_less_than_80_pin_count(sdrb_df)
        df.loc[sdrb_df.index, 'Side'] = port_df_side_added['Side'].values
        return [port_df_side_added]

    else:
        # Calculate number of parts needed
        n_parts_needed = (len(combined_df) + 79) // 80  # Ceiling division
        sdrb_parts = split_into_n_parts(combined_df, n_parts_needed, max_rows=80, Strict_Population=False)
        return sdrb_parts




