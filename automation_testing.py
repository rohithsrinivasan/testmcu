import os
import time
from playwright.sync_api import sync_playwright

def automate_streamlit(input_dir, output_dir):
    with sync_playwright() as p:
        # Launch browser (visible so you can watch)
        browser = p.chromium.launch(headless=False, slow_mo=500)  # slow_mo makes actions visible
        page = browser.new_page()
        
        # Process each Excel file
        for filename in os.listdir(input_dir):
            if not filename.lower().endswith(('.xlsx', '.csv')):
                continue
                
            file_path = os.path.join(input_dir, filename)
            print(f"\nProcessing {filename}...")
            
            # 1. Open Grouping Page
            page.goto("http://localhost:8501/Grouping_2")
            
            # 2. Upload File
            with page.expect_file_chooser() as fc:
                page.click("text=Upload a exel file")
            file_chooser = fc.value
            file_chooser.set_files(file_path)
            
            # 3. Check "Use database for grouping"
            page.check('label:has-text("Use database for grouping")')
            
            # 4. Wait for and click SideAlloc
            page.wait_for_selector('a[href*="Side_Allocation"]', timeout=30000)
            page.click('a[href*="Side_Allocation"]')
            
            # 5. Handle Download (tries both buttons)
            with page.expect_download() as download_info:
                if page.query_selector('button:has-text("Download Smart Table")'):
                    page.click('button:has-text("Download Smart Table")')
                else:
                    page.click('button:has-text("Download All")')
            
            # Save download
            download = download_info.value
            output_path = os.path.join(output_dir, download.suggested_filename)
            download.save_as(output_path)
            print(f"Saved: {output_path}")
            
            # Small delay before next file
            time.sleep(2)
        
        browser.close()

if __name__ == "__main__":
    # Configure paths (use raw strings for Windows)
    input_directory = r"C:\Users\a5149169\Downloads\Automation_testing"
    output_directory = r"C:\Users\a5149169\Downloads\Automation_testing\results"
    
    
    # Create output directory if needed
    os.makedirs(output_directory, exist_ok=True)
    
    automate_streamlit(input_directory, output_directory)
    print("\nAutomation complete!")
