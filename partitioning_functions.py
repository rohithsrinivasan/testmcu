import SideAllocation_functions as sideallocation
import pandas as pd

'''def partitioning(df_last):
    df = sideallocation.filter_and_sort_by_priority(df_last)

    # Apply filter for power pins and update 'Side' column for power pins
    df['Side'] = df.apply(sideallocation.filter_out_power_pins, args=(df,), axis=1)
    power_df = df[df['Side'].isin(['Left', 'Right'])]
    df.loc[power_df.index, 'Side'] = power_df['Side']

    print("Power DataFrame:", power_df)

    # Handle unfilled rows
    unfilled_df = df[df['Side'].isna()]
    number_of_rows_left = len(unfilled_df)
    print(f"Length of unfilled DataFrame: {number_of_rows_left}")

    df_Part_A = pd.DataFrame()
    
    if number_of_rows_left <= 80:
        print("Only one extra Part")

        df_Part_A = sideallocation.filter_and_sort_by_priority(unfilled_df)
        df_Part_A['Side'] = df_Part_A.apply(lambda row: sideallocation.side_allocation(row, df_Part_A), axis=1)

        # Update unfilled rows in the original DataFrame
        df.loc[unfilled_df.index, 'Side'] = df_Part_A['Side'].values

        print(f"Part A DataFrame: {df_Part_A}")

        # Recheck unfilled rows after allocation
        number_of_rows_left = df['Side'].isna().sum()
        print(f"Length of unfilled DataFrame: {number_of_rows_left}")

        if number_of_rows_left == 0:
            print("Everything is correct and as per expectation")
            print(f"all bins are filled,Initializing empty dataframe ") 
            port_df_side_added = pd.DataFrame()  
            Port_Balance_2 = pd.DataFrame()

        else:
            print("Something is wrong")
            print(f"Unfilled DataFrame: {df[df['Side'].isna()]}")


    elif number_of_rows_left > 80  and any(unfilled_df['Priority'].str.startswith('P_Port')):
        port_df = unfilled_df[unfilled_df['Priority'].str.startswith('P_Port')]
        print(f"Port df : {port_df}")
        print(f"Length of Port DF: {len(port_df)}")

        other_unnamed_df = unfilled_df[~unfilled_df.index.isin(port_df.index)]
        print(f"Length of Other Unnamed DF: {len(other_unnamed_df)}")

        overall_length = len(port_df) + len(other_unnamed_df)
        print(f"Overall length of remaining DataFrame: {overall_length}")

        if len(port_df) < 80 :
            port_df_side_added = assigning_side_for_less_than_80_pin_count(port_df)
            df.loc[port_df.index, 'Side'] = port_df_side_added['Side'].values

            # Recheck unfilled rows after allocation
            number_of_rows_left = df['Side'].isna().sum()
            print(f"Length of unfilled DataFrame: {number_of_rows_left}")

            if number_of_rows_left == 0:
                print("Everything is correct and as per expectation for Port DF")
            else:
                print("Something is wrong for Port DF")
                print(f"Unfilled DataFrame: {df[df['Side'].isna()]}") 


        elif len(port_df) > 80 and len(other_unnamed_df) < 80:
            combined_df = pd.concat([port_df, other_unnamed_df], ignore_index=True)
            print(f"combined_df \n{combined_df}")
            
            # Check if the combined length is less than 160
            if len(combined_df) < 160:
                # Group by 'Priority' to get grouped indices
                grouped_indices = combined_df.groupby('Priority').indices
                
                # Initialize empty DataFrames for splitting
                Port_Part_1 = pd.DataFrame()
                Port_Balance_1 = pd.DataFrame()

                # Initialize counters to manage row limits
                part_1_rows = 0
                max_rows = 80
                
                # Split the data into two parts based on grouped indices
                for priority, indices in grouped_indices.items():
                    group = combined_df.loc[indices]
                    
                    if part_1_rows + len(group) <= max_rows:
                        Port_Part_1 = pd.concat([Port_Part_1, group], ignore_index=True)
                        part_1_rows += len(group)
                    else:
                        Port_Balance_1 = pd.concat([Port_Balance_1, group], ignore_index=True)
                
                # Print the tables
                print("Port_Part_1:")
                print(Port_Part_1)
                print("\nPort_Balance_1:")
                print(Port_Balance_1)

                port_df_side_added = pd.DataFrame()
                Port_Balance_2 = pd.DataFrame()   


            elif len(combined_df) > 160:
                # Group by 'Priority' to get grouped indices
                grouped_indices = combined_df.groupby('Priority').indices
                
                # Initialize empty DataFrames for splitting
                Port_Part_1 = pd.DataFrame()
                Port_Balance_1 = pd.DataFrame()
                Port_Balance_2 = pd.DataFrame()

                # Initialize counters to manage row limits
                part_1_rows = 0
                balance_1_rows = 0
                max_rows = 80  # Maximum rows for each part

                # Split the data into parts based on grouped indices
                for priority, indices in grouped_indices.items():
                    group = combined_df.loc[indices]
                    group_size = len(group)
                    
                    # Assign to Port_Part_1 if space is available
                    if part_1_rows + group_size <= max_rows:
                        Port_Part_1 = pd.concat([Port_Part_1, group], ignore_index=True)
                        part_1_rows += group_size
                    # Assign to Port_Balance_1 if Port_Part_1 is filled
                    elif balance_1_rows + group_size <= max_rows:
                        Port_Balance_1 = pd.concat([Port_Balance_1, group], ignore_index=True)
                        balance_1_rows += group_size
                    # Assign remaining to Port_Balance_2
                    else:
                        Port_Balance_2 = pd.concat([Port_Balance_2, group], ignore_index=True)

                # Print or return results
                print("Port_Part_1 rows:", len(Port_Part_1))
                print("Port_Balance_1 rows:", len(Port_Balance_1))
                print("Port_Balance_2 rows:", len(Port_Balance_2))
                
                # Print the tables
                print("Port_Part_1:")
                print(Port_Part_1)
                print("\nPort_Balance_1:")
                print(Port_Balance_1)
                print("\nPort_Balance_2:")
                print(Port_Balance_2)                

                port_df_side_added = pd.DataFrame()  

        else:
            print(f"Initializing empty dataframe for a seperate port table because all bins are filled") 
            port_df_side_added = pd.DataFrame()            

    else:
        print("You will have to create more Parts")

    # Dictionary to store non-empty DataFrames
    df_dict = {
        'Power Table': power_df,
        'Part A Table': df_Part_A,
        'Port Table': port_df_side_added,
        'Unfilled Table': df[df['Side'].isna()],
        'Port Table - 1': Port_Part_1,
        'Port Table - 2' :  Port_Balance_1,
        'Port Table - 3' :  Port_Balance_2,

    }

    if (len(Port_Part_1) + len(Port_Balance_1) == len(unfilled_df)) or (len(Port_Part_1) + len(Port_Balance_1) + len(Port_Balance_2) == len(unfilled_df)):
        del df_dict['Unfilled Table']

    else:
        print(f"Something wrong with splitting into parts")



    # Filter out empty DataFrames
    df_divided_into_parts = {key: value for key, value in df_dict.items() if not value.empty}

    return df_divided_into_parts'''


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
    Port_Balance_1 = pd.DataFrame()
    Port_Balance_2 = pd.DataFrame()
    Port_Part_1 = pd.DataFrame()

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
        else:
            # Split into three parts
            Port_Part_1, Port_Balance_1, Port_Balance_2 = split_into_three_parts(combined_df, max_rows=80)
    
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