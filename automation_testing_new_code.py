import os
import time
from playwright.sync_api import sync_playwright

def automate_streamlit(input_dir, output_dir):
    failed_files = []

    with sync_playwright() as p:
        # Cedge browser
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=500,
            downloads_path=output_dir
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

            try:
                #Grouping page ku poganum
                page.goto("http://localhost:8501/Grouping_2", timeout=60000)

                
                page.set_input_files('input[type="file"]', file_path)

                
                page.check('label:has-text("Use database for grouping")')

                
                page.wait_for_selector('a[href*="Side_Allocation"]', state="visible", timeout=120000)
                page.click('a[href*="Side_Allocation"]')

                with page.expect_download(timeout=60000) as download_info:
                    if page.get_by_text("Download Smart Table").is_visible():
                        page.get_by_text("Download Smart Table").click()
                    else:
                        page.get_by_text("Download All").click()

                download = download_info.value
                print(f"✅ Saved to: {os.path.join(output_dir, download.suggested_filename)}")

                # this part not working...will come back
                time.sleep(2)

            except Exception as e:
                print(f"❌ Failed to process {filename}. Error: {e}")
                failed_files.append(filename)

        context.close()
        browser.close()


    # If files files fail...must write exception
    print("\n🎉 All files processed.")
    if failed_files:
        print("\n⚠️ The following files failed to process:")
        for f in failed_files:
            print(f" - {f}")
    else:
        print("✅ All files processed successfully with no errors.")

if __name__ == "__main__":

    input_directory = r"C:\Users\a5149169\Downloads\testing_mcumpu_category_3_wise 1\Automation_testing_pptx"
    output_directory = r"C:\Users\a5149169\Downloads\testing_mcumpu_category_3_wise 1\Automation_testing_pptx\Results"
    os.makedirs(output_directory, exist_ok=True)

    automate_streamlit(input_directory, output_directory)
