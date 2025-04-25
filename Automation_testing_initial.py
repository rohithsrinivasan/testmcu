import os
import time
from playwright.sync_api import sync_playwright

def automate_streamlit(input_dir, output_dir):
    with sync_playwright() as p:
        # Launch Edge with visible browser
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=1000  # Slower for visibility
        )
        context = browser.new_context(
            accept_downloads=True,
            viewport={'width': 1280, 'height': 1024}
        )
        page = context.new_page()
        
        # First manual initiation
        page.goto("http://localhost:8501/Grouping_2")
        print("\n👉 PLEASE MANUALLY UPLOAD THE FIRST FILE NOW")
        print("After you see the first file processed, automation will continue...")
        
        # Wait for first file to process
        page.wait_for_selector('a[href*="Side_Allocation"]', timeout=120000)
        
        # Now automate remaining files
        file_list = [f for f in os.listdir(input_dir) if f.lower().endswith(('.xlsx', '.csv'))]
        
        for i, filename in enumerate(file_list):
            if i == 0:  # Skip first file (already done manually)
                continue
                
            file_path = os.path.join(input_dir, filename)
            print(f"\n⚡ Automatically processing {filename}...")
            
            # Return to Grouping page
            page.goto("http://localhost:8501/Grouping_2")
            
            # Automated file upload
            with page.expect_file_chooser() as fc:
                page.click("text=Upload a exel file")
            file_chooser = fc.value
            file_chooser.set_files(file_path)
            
            # Check database grouping
            page.check('label:has-text("Use database for grouping")')
            
            # Process and download
            page.wait_for_selector('a[href*="Side_Allocation"]')
            page.click('a[href*="Side_Allocation"]')
            
            # Handle both download button types
            with page.expect_download() as download_info:
                if page.query_selector('button:has-text("Download Smart Table")'):
                    page.click('button:has-text("Download Smart Table")')
                else:
                    page.click('button:has-text("Download All")')
            
            download = download_info.value
            download.save_as(os.path.join(output_dir, download.suggested_filename))
            print(f"✅ Saved: {download.suggested_filename}")
            
            time.sleep(2)  # Brief pause between files
        
        print("\n🎉 All files processed automatically!")
        context.close()
        browser.close()

if __name__ == "__main__":
    # Configure paths (use your actual paths)
    input_directory = r"C:\Users\a5149169\Downloads\Automation_testing-2"
    output_directory = r"C:\Users\a5149169\Downloads\Automation_testing-2\Results"
    
    os.makedirs(output_directory, exist_ok=True)
    automate_streamlit(input_directory, output_directory)