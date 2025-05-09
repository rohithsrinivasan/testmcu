import SideAllocation_functions as sideallocation
import pandas as pd

def partitioning(df_last):
    # Step 1: Filter and sort by priority
    df = sideallocation.filter_and_sort_by_priority(df_last)

    # Step 2: Apply filter for power pins and update the 'Side' column
    df['Side'] = df.apply(sideallocation.filter_out_power_pins, args=(df,), axis=1)
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
    Port_Part_1 = pd.DataFrame()
    Port_Balance_1 = pd.DataFrame()
    Port_Balance_2 = pd.DataFrame()
    Port_Balance_3 = pd.DataFrame()
    Port_Balance_4 = pd.DataFrame()
    Port_Balance_5 = pd.DataFrame()

    # Handle cases based on the number of unfilled rows
    if number_of_rows_left <= 80:
        print("Only one extra Part")

        df_Part_A = sideallocation.filter_and_sort_by_priority(unfilled_df)
        df_Part_A['Side'] = df_Part_A.apply(lambda row: sideallocation.side_allocation(row, df_Part_A), axis=1)

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

        if len(port_df) < 80:
            port_df_side_added = assigning_side_for_less_than_80_pin_count(port_df)
            df.loc[port_df.index, 'Side'] = port_df_side_added['Side'].values

        elif 80 < len(combined_df) <= 160:
            # Split into Port_Part_1 and Port_Balance_1
            Port_Part_1, Port_Balance_1 = split_into_parts(combined_df, max_rows=80)

        elif 160 < len(combined_df) <= 240:
            # Split into three parts
            Port_Part_1, Port_Balance_1, Port_Balance_2 = split_into_three_parts(combined_df, max_rows=80)

        elif 240 < len(combined_df) <= 320:
            # Split into four parts
            Port_Part_1, Port_Balance_1, Port_Balance_2, Port_Balance_3 = split_into_four_parts(combined_df, max_rows=80)

        elif 320 < len(combined_df) <= 400:
            # Split into five parts
            Port_Part_1, Port_Balance_1, Port_Balance_2, Port_Balance_3, Port_Balance_4 = split_into_five_parts(combined_df, max_rows=80)

        elif 400 < len(combined_df) <= 480:
            # Split into six parts
            Port_Part_1, Port_Balance_1, Port_Balance_2, Port_Balance_3, Port_Balance_4, Port_Balance_5 = split_into_six_parts(combined_df, max_rows=80)

        else:
            print("Too many unassigned ports. Consider dynamic chunking or extending the part logic.")

    
    else:
        print("You will have to create more Parts")

    # Step 4: Construct the dictionary of DataFrames
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
        'Port Table - 6': Port_Balance_5,
    }

    # Clean up the dictionary by removing empty DataFrames
    df_dict = {key: value for key, value in df_dict.items() if not value.empty}

    # Final validation of splitting logic
    total_rows_processed = sum(len(table) for table in df_dict.values())
    if total_rows_processed != len(df):
        print("Something went wrong with splitting into parts.")
        print(f"Total rows processed: {total_rows_processed}, Original rows: {len(df)}")

    return df_dict


# Utility function to split into two parts
def split_into_parts(df, max_rows=80):
    grouped_indices = df.groupby('Priority').indices
    part_1 = pd.DataFrame()
    balance_1 = pd.DataFrame()
    part_1_rows = 0

    for priority, indices in grouped_indices.items():
        group = df.loc[indices]
        if part_1_rows + len(group) <= max_rows:
            part_1 = pd.concat([part_1, group], ignore_index=True)
            part_1_rows += len(group)
        else:
            balance_1 = pd.concat([balance_1, group], ignore_index=True)

    return part_1, balance_1

# Utility function to split into three parts
def split_into_three_parts(df, max_rows=80):
    grouped_indices = df.groupby('Priority').indices
    part_1 = pd.DataFrame()
    balance_1 = pd.DataFrame()
    balance_2 = pd.DataFrame()
    part_1_rows = 0
    balance_1_rows = 0

    for priority, indices in grouped_indices.items():
        group = df.loc[indices]
        if part_1_rows + len(group) <= max_rows:
            part_1 = pd.concat([part_1, group], ignore_index=True)
            part_1_rows += len(group)
        elif balance_1_rows + len(group) <= max_rows:
            balance_1 = pd.concat([balance_1, group], ignore_index=True)
            balance_1_rows += len(group)
        else:
            balance_2 = pd.concat([balance_2, group], ignore_index=True)

    return part_1, balance_1, balance_2

def split_into_four_parts(df, max_rows=80):
    grouped_indices = df.groupby('Priority').indices
    parts = [pd.DataFrame() for _ in range(4)]
    part_rows = [0] * 4

    for priority, indices in grouped_indices.items():
        group = df.loc[indices]
        placed = False
        for i in range(4):
            if part_rows[i] + len(group) <= max_rows:
                parts[i] = pd.concat([parts[i], group], ignore_index=True)
                part_rows[i] += len(group)
                placed = True
                break
        if not placed:
            parts[-1] = pd.concat([parts[-1], group], ignore_index=True)

    return tuple(parts)


def split_into_five_parts(df, max_rows=80):
    grouped_indices = df.groupby('Priority').indices
    parts = [pd.DataFrame() for _ in range(5)]
    part_rows = [0] * 5

    for priority, indices in grouped_indices.items():
        group = df.loc[indices]
        placed = False
        for i in range(5):
            if part_rows[i] + len(group) <= max_rows:
                parts[i] = pd.concat([parts[i], group], ignore_index=True)
                part_rows[i] += len(group)
                placed = True
                break
        if not placed:
            parts[-1] = pd.concat([parts[-1], group], ignore_index=True)

    return tuple(parts)


def split_into_six_parts(df, max_rows=80):
    grouped_indices = df.groupby('Priority').indices
    parts = [pd.DataFrame() for _ in range(6)]
    part_rows = [0] * 6

    for priority, indices in grouped_indices.items():
        group = df.loc[indices]
        placed = False
        for i in range(6):
            if part_rows[i] + len(group) <= max_rows:
                parts[i] = pd.concat([parts[i], group], ignore_index=True)
                part_rows[i] += len(group)
                placed = True
                break
        if not placed:
            parts[-1] = pd.concat([parts[-1], group], ignore_index=True)

    return tuple(parts)


def assigning_side_for_priority_for_dataframes_within_dictionary(dfs):
    final_dfs = {}

    for title, df in dfs.items():
        df_copy = df.copy()

        df_new = assigning_side_for_less_than_80_pin_count(df_copy)
        
        # Apply sorting based on 'Side'
        ascending_order_df = df_new[df_new['Side'] == 'Left']
        ascending_order_df = sideallocation.assigning_ascending_order_for_similar_group(ascending_order_df)

        descending_order_df = df_new[df_new['Side'] == 'Right']
        descending_order_df = sideallocation.assigning_descending_order_for_similar_group(descending_order_df)

        # Concatenate the two sorted DataFrames back together
        final_df = pd.concat([ascending_order_df, descending_order_df]).reset_index(drop=True)
        
        # Store the modified DataFrame in the final dictionary
        final_dfs[title] = final_df
    
    return final_dfs


def assigning_side_for_priority_for_dataframes_within_dictionary(dfs):
    final_dfs = {}

    for title, df in dfs.items():
        df_copy = df.copy()
        
        # Special handling for Power Table
        if title == 'Power Table':
            # Apply power pin filtering directly
            df_copy['Side'] = df_copy.apply(lambda row: filter_out_power_pins(row, df_copy), axis=1)
            
            # Apply sorting based on 'Side'
            ascending_order_df = df_copy[df_copy['Side'] == 'Left']
            ascending_order_df = sideallocation.assigning_ascending_order_for_similar_group(ascending_order_df)

            descending_order_df = df_copy[df_copy['Side'] == 'Right']
            descending_order_df = sideallocation.assigning_descending_order_for_similar_group(descending_order_df)

            # Concatenate the two sorted DataFrames back together
            final_df = pd.concat([ascending_order_df, descending_order_df]).reset_index(drop=True)
        else:
            # Normal processing for other tables
            df_new = assigning_side_for_less_than_80_pin_count(df_copy)
            
            # Apply sorting based on 'Side'
            ascending_order_df = df_new[df_new['Side'] == 'Left']
            ascending_order_df = sideallocation.assigning_ascending_order_for_similar_group(ascending_order_df)

            descending_order_df = df_new[df_new['Side'] == 'Right']
            descending_order_df = sideallocation.assigning_descending_order_for_similar_group(descending_order_df)

            # Concatenate the two sorted DataFrames back together
            final_df = pd.concat([ascending_order_df, descending_order_df]).reset_index(drop=True)
        
        # Store the modified DataFrame in the final dictionary
        final_dfs[title] = final_df
    
    return final_dfs


def assigning_side_for_less_than_80_pin_count(df):
    df_Part = sideallocation.filter_and_sort_by_priority(df)
    df_Part['Side'] = df_Part.apply(lambda row: sideallocation.side_allocation(row, df_Part), axis=1)

    return df_Part


def filter_out_power_pins(row, df):
    df['Priority'] = df['Priority'].fillna('')

    left_power_mask = df['Priority'].str.startswith('A')
    #right_power_mask = df['Priority'].str.startswith('Z','Y')
    right_power_mask = df['Priority'].str.startswith(('Z', 'Y'))


    # Create lists of indices for left and right power using the masks
    left_power = df.index[left_power_mask].tolist()
    right_power = df.index[right_power_mask].tolist()

    # Return based on the allocation
    if row.name in left_power:
        return 'Left'
    elif row.name in right_power:
        return 'Right'
    else:
        return None

def convert_dict_to_list(df_dict):
    return [df for df in df_dict.values()]