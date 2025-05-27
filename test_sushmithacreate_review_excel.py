import json
import pandas as pd
import os

def process_json_folder(folder_path, excel_file_path):
    """
    Processes all JSON files in a given folder, with each JSON file's content
    becoming a separate sheet in an Excel workbook. Each sheet will have
    group names as column headers and pin names as values.

    Args:
        folder_path (str): The path to the folder containing the JSON files.
        excel_file_path (str): The path to the output Excel workbook.
    """
    writer = pd.ExcelWriter(excel_file_path, engine='xlsxwriter')  # Use xlsxwriter for multiple sheets

    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

    if not json_files:
        print(f"No JSON files found in the folder: {folder_path}")
        return

    for json_file in json_files:
        json_file_path = os.path.join(folder_path, json_file)
        sheet_name = os.path.splitext(json_file)[0]  # Use filename without extension as sheet name

        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: JSON file not found at {json_file_path}")
            continue
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {json_file_path}")
            continue

        df_data = {}
        for group_name, pins in data.items():
            df_data[group_name] = pd.Series(pins)

        df = pd.DataFrame(df_data)

        try:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Processed {json_file} and added sheet '{sheet_name}' to the Excel workbook.")
        except Exception as e:
            print(f"Error writing sheet '{sheet_name}' to Excel: {e}")

    try:
        writer.close()
        print(f"Successfully created Excel workbook at {excel_file_path}")
    except Exception as e:
        print(f"Error closing the Excel writer: {e}")

if __name__ == "__main__":
    # Replace 'path/to/your/json/folder' with the actual path to the folder
    json_folder = 'pin_database\mcu_database_restructured'
    output_excel_file = 'dupe_database_newest.xlsx'
    process_json_folder(json_folder, output_excel_file)