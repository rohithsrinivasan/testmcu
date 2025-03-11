import argparse
import pandas as pd
from tabula import read_pdf
import functions as f
import grouping_functions
import SideAllocation_functions
import partitioning_functions
import time
import datetime
import sys

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="SymbolGen CLI: Generate pin tables from PDFs or CSVs.")
    parser.add_argument("--pdf", type=str, help="Path to the PDF file.")
    parser.add_argument("--csv", type=str, help="Path to the CSV file (for non-standard datasheets).")
    parser.add_argument("--part_number", type=str, required=True, help="Part number for processing.")
    parser.add_argument("--device_category", type=str, default="MCU/MPU", choices=["MCU/MPU", "Power", "Clock & Timing", "Analog", "Interface", "Wireless & Connectivity"], help="Device category.")
    parser.add_argument("--grouping_strategy", type=str, default="Algorithm", choices=["Algorithm", "LLM Model", "Database"], help="Grouping strategy.")
    parser.add_argument("--layout_style", type=str, default="DIL", choices=["DIL", "Connector", "Quad"], help="Layout style.")
    parser.add_argument("--non_standard", action="store_true", help="Flag for non-standard datasheets.")
    args = parser.parse_args()

    # Validate inputs
    if not args.pdf and not args.csv:
        print("Error: Either --pdf or --csv must be provided.")
        sys.exit(1)

    if args.non_standard and not args.csv:
        print("Error: --csv is required for non-standard datasheets.")
        sys.exit(1)

    # Process the input file
    if args.pdf:
        print("Processing PDF file...")
        with open(args.pdf, "rb") as input_buffer:
            part_number, number_of_pins, package_type, package_code = f.part_number_details(args.part_number, input_buffer)
            pin_table = f.extracting_pin_tables(input_buffer, part_number, number_of_pins, package_type, package_code)
    elif args.csv:
        print("Processing CSV file...")
        df = pd.read_csv(args.csv)
        required_columns = ["Pin Designator", "Pin Display Name", "Electrical Type", "Pin Alternate Name"]
        df = df[required_columns]
        pin_table = df

    # Grouping logic
    print("Performing grouping...")
    before_grouping_flag, added_empty_grouping_column = grouping_functions.check_excel_format(pin_table)
    if args.grouping_strategy == "Algorithm":
        pin_grouping_table = grouping_functions.assigning_grouping_as_per_algorithm(added_empty_grouping_column)
    elif args.grouping_strategy == "Database":
        json_file = "Database.json"
        pin_grouping_table = grouping_functions.assigning_grouping_as_per_database(added_empty_grouping_column, json_file)
    elif args.grouping_strategy == "LLM Model":
        response, pin_grouping_table = grouping_functions.assigning_grouping_as_per_LLM(added_empty_grouping_column)
        print(f"Type of device: {response.text}")

    # Check for empty groupings
    no_grouping_assigned = grouping_functions.check_empty_groupings(pin_grouping_table)
    if not no_grouping_assigned.empty:
        print("Please fill in group values for these:")
        print(no_grouping_assigned)
        sys.exit(1)

    # Side allocation logic
    print("Performing side allocation...")
    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping', 'Priority']
    additional_column = 'Priority'
    before_priority_flag, added_empty_priority_column = SideAllocation_functions.check_excel_format(pin_grouping_table, required_columns, additional_column)
    priority_added = SideAllocation_functions.assigning_priority_for_group(added_empty_priority_column)

    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping', 'Priority', 'Side']
    additional_column = 'Side'
    before_side_flag, added_empty_side_column = SideAllocation_functions.check_excel_format(priority_added, required_columns, additional_column)

    if len(added_empty_side_column) < 80:
        side_added = SideAllocation_functions.assigning_side_for_priority(added_empty_side_column)
    else:
        df_dict = partitioning_functions.partitioning(added_empty_side_column)
        side_added_dict = partitioning_functions.assigning_side_for_priority_for_dataframes_within_dictionary(df_dict)
        side_added = side_added_dict

    # Layout style logic
    print("Applying layout style...")
    required_columns = ['Pin Designator', 'Pin Display Name', 'Electrical Type', 'Pin Alternate Name', 'Grouping', 'Priority', 'Side', 'Changed Grouping']
    additional_column = 'Changed Grouping'
    before_new_grouping_flag, added_empty_new_grouping_column = SideAllocation_functions.check_excel_format(side_added, required_columns, additional_column)
    grouping_changed = SideAllocation_functions.Dual_in_line_as_per_Renesas(added_empty_new_grouping_column)
    print(f"Grouping_Changed : {grouping_changed}")

'''    # Save the final output
    timestamp = datetime.datetime.now().strftime("%d-%m_%H:%M")
    if isinstance(grouping_changed, pd.DataFrame):
        grouping_changed = SideAllocation_functions.final_filter(grouping_changed)
        filename = f"{args.part_number}_SmartPinTable_{timestamp}.csv"
        grouping_changed.to_csv(filename, index=False)
        print(f"Output saved to {filename}")
    elif isinstance(grouping_changed, dict):
        filename = f"{args.part_number}_SmartPinTable_{timestamp}.xlsx"
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in grouping_changed.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Output saved to {filename}")'''

if __name__ == "__main__":
    main()