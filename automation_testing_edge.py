import os
import time
from playwright.sync_api import sync_playwright

def automate_streamlit(input_dir, output_dir):
    with sync_playwright() as p:
        # Configure Edge browser with downloads
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,  # Visible so you can monitor
            slow_mo=500,    # Slower execution for reliability
            downloads_path=output_dir  # Direct downloads to your folder
        )
        context = browser.new_context(
            accept_downloads=True,
            viewport={'width': 1280, 'height': 1024}
        )
        page = context.new_page()

        # Process all files
        for filename in os.listdir(input_dir):
            if not filename.lower().endswith(('.xlsx', '.csv')):
                continue

            file_path = os.path.join(input_dir, filename)
            print(f"\n🚀 Processing {filename}...")

            # 1. Navigate to Grouping page
            page.goto("http://localhost:8501/Grouping_2", timeout=60000)
            
            # 2. Automated file upload
            page.set_input_files(
                'input[type="file"]',  # Targets the file upload element directly
                file_path
            )
            
            # 3. Enable database grouping
            page.check('label:has-text("Use database for grouping")')
            
            # 4. Wait for and click SideAlloc
            page.wait_for_selector('a[href*="Side_Allocation"]', state="visible", timeout=120000)
            page.click('a[href*="Side_Allocation"]')
            
            # 5. Handle download (both button types)
            with page.expect_download(timeout=60000) as download_info:
                if page.get_by_text("Download Smart Table").is_visible():
                    page.get_by_text("Download Smart Table").click()
                else:
                    page.get_by_text("Download All").click()
            
            # Let Playwright handle the download automatically
            download = download_info.value
            print(f"✅ Saved to: {os.path.join(output_dir, download.suggested_filename)}")
            
            # Brief pause before next file
            time.sleep(2)
        
        print("\n🎉 All files processed successfully!")
        context.close()
        browser.close()

if __name__ == "__main__":
    # Configure these paths (use raw strings for Windows)

    input_directory = r"C:\Users\a5149169\Downloads\Automation_testing-2"
    output_directory = r"C:\Users\a5149169\Downloads\Automation_testing-2\Results"
    
    # Create output directory if needed
    os.makedirs(output_directory, exist_ok=True)
    
    automate_streamlit(input_directory, output_directory)