import argparse
import pandas as pd
from tabula import read_pdf
import functions as f
import time
import part_number_details_functions

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="SymbolGen CLI Tool")
    parser.add_argument("--file", type=str, required=True, help="Path to the PDF file")
    parser.add_argument("--part_number", type=str, required=True, help="Part number")
    args = parser.parse_args()

    # Process the file and part number
    print("Processing...")
    time.sleep(5)  # Simulate processing time

    try:
        # Call functions to process the file and part number
        part_number, number_of_pins, package_type, package_code = f.part_number_details(
            args.part_number, args.file
        )
        pin_table = f.extracting_pin_tables(
            args.file, part_number, number_of_pins, package_type, package_code
        )

        # Display results
        print("Done!")
        print(f"Part Number: {part_number}")
        print(f"Number of Pins: {number_of_pins}")
        print(f"Package Type: {package_type}")
        print(f"Package Code: {package_code}")
        print("Pin Table:")
        print(pin_table)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()


