import fitz  # PyMuPDF
import os
import pandas as pd
import tempfile

def find_between_markers(text, start_marker="A.1", end_marker="A.2"):
    start = text.find(start_marker)
    end = text.find(end_marker)
    print(f"[DEBUG] Start index of '{start_marker}': {start}")
    print(f"[DEBUG] End index of '{end_marker}': {end}")
    if start == -1 or end == -1 or start >= end:
        return ""
    return text[start:end]

def check_for_info_line(text):
    lines = text.splitlines()
    for line in lines:
        if "For detail information" in line:
            print(f"[INFO] Line found: {line}")
            return True
    print("[INFO] No line with 'For detail information' found.")
    return False

def extract_embedded_excel(doc):
    print("[INFO] Checking for embedded files...")
    if doc.embfile_count() == 0:
        print("[INFO] No embedded files found in the PDF.")
        return None

    for name in doc.embfile_names():
        print(f"[DEBUG] Found embedded file: {name}")
        if name.lower().endswith(".xlsx"):
            ef = doc.embfile_get(name)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(ef["file"])
                tmp_path = tmp.name
                print(f"[INFO] Saved embedded Excel file to: {tmp_path}")
                return tmp_path

    print("[WARNING] No embedded Excel (.xlsx) file found.")
    return None

def read_excel_file(path):
    print(f"[INFO] Reading Excel file: {path}")
    try:
        df = pd.read_excel(path)
        print("[INFO] Excel file content:")
        print(df)
    except Exception as e:
        print(f"[ERROR] Failed to read Excel file: {e}")

def main(pdf_path):
    print(f"[INFO] Opening PDF file: {pdf_path}")
    doc = fitz.open(pdf_path)

    full_text = ""
    for i, page in enumerate(doc):
        print(f"[DEBUG] Extracting text from page {i}")
        full_text += page.get_text()

    section_text = find_between_markers(full_text, "A.1", "A.2")

    if check_for_info_line(section_text):
        excel_path = extract_embedded_excel(doc)
        if excel_path:
            read_excel_file(excel_path)
        else:
            print("[INFO] No Excel file extracted.")
    else:
        print("[INFO] 'For detail information' not found between A.1 and A.2")


if __name__ == "__main__":
    # Replace with your PDF file path
    main(r"C:\Users\a5149169\Downloads\RH850-EDI-Appendix-Attachments.pdf")
