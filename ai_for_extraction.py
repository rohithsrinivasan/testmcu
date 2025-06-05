import streamlit as st
import google.generativeai as genai
import json
import PyPDF2
import docx

import os
from dotenv import load_dotenv
import google.generativeai as genai

def get_and_validate_api_key():
    """Get API key from .env and validate it with Gemini"""
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY')
    
    if not api_key:
        st.error("❌ GOOGLE_API_KEY not found in .env file")
        return None
    
    # Display masked API key
    masked_key = f"{api_key[:8]}{'*' * (len(api_key) - 12)}{api_key[-4:]}"
    st.info(f"🔑 Using API Key: {masked_key}")
    
    # Validate API key
    try:
        genai.configure(api_key=api_key)
        # Test with a minimal request
        model = genai.GenerativeModel('gemini-1.5-flash')
        test_response = model.generate_content("Test")
        st.success("✅ API Key is valid and active")
        return api_key
    except genai.types.BrokenResponseError:
        st.error("❌ API Key is invalid or expired")
        return None
    except Exception as e:
        st.error(f"❌ API validation failed: {str(e)[:100]}")
        return None


def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_text_from_txt(file):
    """Extract text from TXT file"""
    try:
        return str(file.read(), "utf-8")
    except Exception as e:
        st.error(f"Error reading TXT: {e}")
        return ""

def process_document(uploaded_file):
    """Process uploaded document and extract text"""
    if uploaded_file is not None:
        file_type = uploaded_file.type
        
        if file_type == "application/pdf":
            return extract_text_from_pdf(uploaded_file)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return extract_text_from_docx(uploaded_file)
        elif file_type == "text/plain":
            return extract_text_from_txt(uploaded_file)
        else:
            st.error("Unsupported file type. Please upload PDF, DOCX, or TXT files.")
            return ""
    return ""

def setup_gemini(api_key: str):
    """Initialize Gemini API"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.session_state.gemini_model = model
        return True
    except Exception as e:
        st.error(f"Error setting up Gemini: {e}")
        return False

def get_ai_response(question: str, document_content: str) -> str:
    """Get response from Gemini API"""
    if not st.session_state.gemini_model:
        return "Please configure Gemini API key first."
    
    try:
        prompt = f"""
        Based on the following document content, please answer the question accurately and concisely.
        
        Document Content:
        {document_content[:10000]}  # Limit to first 10k characters
        
        Question: {question}
        
        Answer:
        """
        
        response = st.session_state.gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating response: {e}"

def display_chat_interface():
    """
    Display the main chat interface for document Q&A
    """
    # Main chat interface
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Part Search Query")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if question := st.chat_input("Ask a question about Part-Pin info"):
            if not st.session_state.document_content:
                st.error("Please upload a document first!")
            elif not st.session_state.gemini_model:
                st.error("Please configure your Gemini API key first!")
            else:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": question})
                with st.chat_message("user"):
                    st.markdown(question)
                
                # Get AI response
                with st.chat_message("assistant"):
                    with st.spinner("Extracting Pin Information..."):
                        response = get_ai_response(question, st.session_state.document_content)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

    with col2:
        st.subheader("📊 Stats")
        if st.session_state.document_content:
            st.metric("Document Length", f"{len(st.session_state.document_content):,} chars")
            st.metric("Words", f"{len(st.session_state.document_content.split()):,}")
            st.metric("Chat Messages", len(st.session_state.messages))
        else:
            st.info("Upload a Datasheet to see stats")

    # Footer
    st.divider()

def perform_ai_extraction(input_part_number, model, file_content):
    st.text("Starting AI extraction process...")
    st.text(f"Part Number received: {input_part_number}")

    # You can add a check for API key existence and validity if needed
    # For example:
    # if not genai.get_client().api_key:
    #     st.error("API Key not found or not configured!")
    #     return
    # st.text("API Key found and potentially valid (further validation depends on API call success).")

    with st.spinner('Processing with Gemini API...'):
        try:
            # Craft the prompt for Gemini, including the instruction to read the document content
            prompt_parts = [
                file_content, # Pass the document content as a part
                f'''
                You are an electrical design engineer. Here is a datasheet of a MCU having different sections such as overview, electrical characteristics and ECAD information. You have to focus on the ECAD Information section and takes out the details:
                1. Pin configuration: It will be having the list of pins based on the part numbers. For each pin, extract the "Pin Number", "Primary Pin Name", "Primary Electrical Type", and "Alternate Pin Name(s)".
                2. Also extract the "Part Number", "Number of Pins", "Package Type", and "Package Code" from the datasheet.

                Structure the output as a JSON file with the following schema:

                {{
                    "part_number": "<extracted_part_number>",
                    "number_of_pins": <extracted_number_of_pins>,
                    "package_type": "<extracted_package_type>",
                    "package_code": "<extracted_package_code>",
                    "pin_table": [
                        {{
                            "Pin Number": "<pin_number>",
                            "Primary Pin Name": "<primary_pin_name>",
                            "Primary Electrical Type": "<primary_electrical_type>",
                            "Alternate Pin Name(s)": "<alternate_pin_name(s)>"
                        }}
                        // ... more pin objects for all 48 pins
                    ]
                }}
                Ensure "Alternate Pin Name(s)" is '-' if no alternate names are present.
                For "Primary Electrical Type", infer from the pin description (e.g., 'Power', 'Input', 'Output').
                The specific part number to focus on for this extraction is {input_part_number}.
                '''
            ]

            st.text("Debug: Sending prompt and file content to Gemini API...")
            # print("Debug: Prompt parts being sent:", prompt_parts) # For terminal debug if needed

            # Call Gemini API with structured response configuration
            response = model.generate_content(
                prompt_parts, # Pass the list of parts, including file_content
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=
                    {
                        "type": "OBJECT",
                        "properties": {
                            "part_number": {"type": "STRING"},
                            "number_of_pins": {"type": "INTEGER"},
                            "package_type": {"type": "STRING"},
                            "package_code": {"type": "STRING"},
                            "pin_table": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "Pin Number": {"type": "STRING"},
                                        "Primary Pin Name": {"type": "STRING"},
                                        "Primary Electrical Type": {"type": "STRING"},
                                        "Alternate Pin Name(s)": {"type": "STRING"}
                                    },
                                    "required": [
                                        "Pin Number",
                                        "Primary Pin Name",
                                        "Primary Electrical Type",
                                        "Alternate Pin Name(s)"
                                    ]
                                }
                            }
                        },
                        "required": [
                            "part_number",
                            "number_of_pins",
                            "package_type",
                            "package_code",
                            "pin_table"
                        ]
                    }
                )
            )

            st.text("Debug: Gemini API response received.")
            # print("Debug: Raw response from Gemini API:", response.text) # For terminal debug if needed

            # Access the content from the response
            extracted_data = json.loads(response.text)
            st.session_state.extracted_json_data = extracted_data

            st.success("AI Extraction Done!")
            st.text("Debug: Data stored in session_state for download and display.")

        except Exception as e:
            st.error(f"Error during AI extraction: {e}")
            st.warning("Please ensure your Gemini API key is valid and the model is accessible.")
            st.text(f"Debug: An error occurred: {e}")

    # Download JSON button
    if "extracted_json_data" in st.session_state and st.session_state.extracted_json_data:
        json_string = json.dumps(st.session_state.extracted_json_data, indent=4)
        st.download_button(
            label="Download Extracted Data as JSON",
            data=json_string,
            file_name=f"{input_part_number}_details.json" if input_part_number else "extracted_details.json",
            mime="application/json",
        )
        st.text("Debug: Download button displayed.")

    # Conditional navigation/display
    if "page" in st.session_state and st.session_state["page"] == "grouping":
        st.page_link("pages/01_Grouping_2.py", label="Grouping 2.0")
        st.text("Debug: Navigating to Grouping 2.0 page based on session state.")
    else:
        st.write("Pin table displayed:")
        if "extracted_json_data" in st.session_state and st.session_state.extracted_json_data:
            st.json(st.session_state.extracted_json_data) # Display the extracted JSON directly
        st.text("Debug: Extracted JSON data displayed.")


########################################

import streamlit as st
import json
import re

def display_chat_interface_2():
    """
    Display the main chat interface for document Q&A with automatic part number extraction
    and pin table extraction functionality
    """
    # Fixed first prompt (hidden from user)
    FIXED_FIRST_PROMPT = """List out all the Part Numbers and their Pin count and Package as a json from this document
Example:
  {"Part Number": "R7FA2E2A33CNK#AA1", "Pin Count": 24, "Package": "HWQFN"},"""
    
    # Fixed second prompt template (hidden from user)
    FIXED_SECOND_PROMPT_TEMPLATE = """Extract Pin Table from the Document for the Part Number {part_number}. Response should be in json like this Example: {{"Pin Designator" : "A1", "Pin Name": "SWDIO", "Electrical Type": "I/O", "Alternate Pin Names": "P108/AGTOA1_B/GTOULO_C/GTIOC7B_C/TXD9_H/MOSI9_H/SDA9_H/CTS9_RTS9_B/SS9_B/MOSIA_C/IRQ5_C"}}"""
    
    # Initialize session state variables
    if 'part_numbers_list' not in st.session_state:
        st.session_state.part_numbers_list = []
    if 'part_numbers_response' not in st.session_state:
        st.session_state.part_numbers_response = ""
    if 'pin_table_responses' not in st.session_state:
        st.session_state.pin_table_responses = {}
    
    # Step 1: Process document automatically if available (First Prompt - Hidden)
    if (st.session_state.document_content and 
        st.session_state.gemini_model and 
        not st.session_state.part_numbers_response):
        
        with st.spinner("Processing document for part numbers..."):
            response = get_ai_response(FIXED_FIRST_PROMPT, st.session_state.document_content)
            st.session_state.part_numbers_response = response
            st.session_state.part_numbers_list = extract_part_numbers_from_response(response)
    
    # Main interface
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("Upload Renesas Datasheet")
        
        # Display Part Numbers section if we have processed content
        if st.session_state.part_numbers_response:
            st.subheader("📋 Part Number List")
            st.markdown(st.session_state.part_numbers_response)
            st.divider()
        
        # Display pin table responses if any
        if st.session_state.pin_table_responses:
            st.subheader("Pin Table")
            for part_num, response in st.session_state.pin_table_responses.items():
                st.markdown(f"**Part Number: {part_num}**")
                st.markdown(response)
                st.divider()
        
        # Single chat input for part numbers
        if part_number_input := st.chat_input("Enter a part number to get its pin table (e.g., R7FA2E2A33CBY#HC1)..."):
            if not st.session_state.document_content:
                st.error("Please upload a document first!")
            elif not st.session_state.gemini_model:
                st.error("Please configure your Gemini API key first!")
            else:
                # Check if the entered part number exists in our list
                part_number_clean = part_number_input.strip()
                
                # Step 2: Process the part number (Second Prompt - Hidden)
                with st.spinner(f"Extracting pin table for {part_number_clean}..."):
                    second_prompt = FIXED_SECOND_PROMPT_TEMPLATE.format(part_number=part_number_clean)
                    pin_response = get_ai_response(second_prompt, st.session_state.document_content)
                    
                    # Store the response
                    st.session_state.pin_table_responses[part_number_clean] = pin_response
                
                # Rerun to show the new response
                st.rerun()
    
    with col2:
        st.header("📊 Stats")
        if st.session_state.document_content:
            st.metric("Document Length", f"{len(st.session_state.document_content):,} chars")
            st.metric("Words", f"{len(st.session_state.document_content.split()):,}")
            
            # Show part numbers count if available
            if st.session_state.part_numbers_list:
                st.metric("Part Numbers Found", len(st.session_state.part_numbers_list))
            
            # Show pin tables extracted
            if st.session_state.pin_table_responses:
                st.metric("Pin Tables Extracted", len(st.session_state.pin_table_responses))
        else:
            st.info("Upload a Datasheet to see stats")
        
        # Show available part numbers for reference
        if st.session_state.part_numbers_list:
            st.subheader("Available Part Numbers")
            for part_num in st.session_state.part_numbers_list[:5]:  # Show first 5
                st.code(part_num, language=None)
            if len(st.session_state.part_numbers_list) > 5:
                st.caption(f"... and {len(st.session_state.part_numbers_list) - 5} more")
    
    # Footer
    st.divider()

def extract_part_numbers_from_response(response_content):
    """
    Extract part numbers from the AI response content
    Handles both JSON format and plain text format
    """
    part_numbers = []
    
    try:
        # Try to parse as JSON first
        if response_content.strip().startswith('[') or response_content.strip().startswith('{'):
            # Handle JSON array format
            if response_content.strip().startswith('['):
                data = json.loads(response_content)
                for item in data:
                    if isinstance(item, dict) and "Part Number" in item:
                        part_numbers.append(item["Part Number"])
            else:
                # Handle single JSON object format
                data = json.loads(response_content)
                if "Part Number" in data:
                    part_numbers.append(data["Part Number"])
        else:
            # Try to extract part numbers using regex patterns
            patterns = [
                r'R7FA[A-Z0-9]+#[A-Z0-9]+',  # Renesas part number pattern
                r'"Part Number":\s*"([^"]+)"',  # JSON format
                r'Part Number:\s*([A-Z0-9#]+)',  # Plain text format
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response_content, re.IGNORECASE)
                part_numbers.extend(matches)
    
    except (json.JSONDecodeError, KeyError):
        # If JSON parsing fails, try regex extraction
        patterns = [
            r'R7FA[A-Z0-9]+#[A-Z0-9]+',  # Renesas part number pattern
            r'"Part Number":\s*"([^"]+)"',  # JSON format
            r'Part Number:\s*([A-Z0-9#]+)',  # Plain text format
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response_content, re.IGNORECASE)
            part_numbers.extend(matches)
    
    # Remove duplicates and return
    return list(set(part_numbers))