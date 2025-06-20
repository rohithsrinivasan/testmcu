import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageGrab
import io
import base64
import os
import time
from datetime import datetime
import json
import requests
import google.generativeai as genai
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Pinout Diagram Extractor",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="expanded"
)

class PinoutExtractor:
    def __init__(self):
        self.image_dir = Path("captured_images")
        self.image_dir.mkdir(exist_ok=True)
        
    def setup_gemini(self, api_key):
        """Setup Gemini API"""
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            st.session_state.gemini_model = model
            return True
        except Exception as e:
            st.error(f"Failed to setup Gemini API: {str(e)}")
            return False
    
    def capture_screen_area(self):
        """Stage 1: Screen capture functionality"""
        st.header("🎯 Stage 1: Capture Pinout Diagram")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("📋 **Instructions:**\n"
                   "1. Click 'Start Screen Capture' button\n"
                   "2. Use your system's screenshot tool (Windows: Snipping Tool, Mac: Cmd+Shift+4)\n"
                   "3. Save the image and upload it using the file uploader below")
        
        with col2:
            if st.button("🖼️ Start Screen Capture", type="primary"):
                st.success("📸 Ready to capture! Use your system's screenshot tool now.")
                st.balloons()
        
        # File uploader for captured image
        uploaded_file = st.file_uploader(
            "📁 Upload your captured pinout image",
            type=['png', 'jpg', 'jpeg', 'bmp'],
            help="Upload the pinout diagram you captured"
        )
        
        if uploaded_file is not None:
            # Save uploaded image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pinout_{timestamp}.{uploaded_file.name.split('.')[-1]}"
            filepath = self.image_dir / filename
            
            # Save image to local directory
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Store in session state
            st.session_state.captured_image = uploaded_file
            st.session_state.image_path = str(filepath)
            
            st.success(f"✅ Image saved to: {filepath}")
            
            # Display captured image
            image = Image.open(uploaded_file)
            st.image(image, caption="Captured Pinout Diagram", use_column_width=True)
            
            # Move to next stage
            if st.button("➡️ Proceed to Extraction", type="primary"):
                st.session_state.current_stage = "extract"
                st.rerun()
    
    def extract_pinout_data(self):
        """Stage 3: AI-powered pinout extraction"""
        st.header("🤖 Stage 3: AI Pinout Extraction")
        
        if 'captured_image' not in st.session_state:
            st.warning("⚠️ No image captured yet. Please go back to Stage 1.")
            return
        
        # API Key input
        api_key = st.text_input(
            "🔑 Enter your Gemini API Key",
            type="password",
            help="Get your API key from https://makersuite.google.com/app/apikey"
        )
        
        if not api_key:
            st.info("💡 Please enter your Gemini API key to proceed with extraction")
            return
        
        # Setup Gemini if not already done
        if 'gemini_model' not in st.session_state:
            if self.setup_gemini(api_key):
                st.success("✅ Gemini API configured successfully!")
            else:
                return
        
        # Display image for reference
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📷 Captured Image")
            image = Image.open(st.session_state.captured_image)
            st.image(image, use_column_width=True)
        
        with col2:
            st.subheader("⚙️ Extraction Settings")
            
            # Extraction options
            extract_descriptions = st.checkbox("Include pin descriptions", value=True)
            extract_functions = st.checkbox("Extract alternate functions", value=True)
            device_type = st.selectbox(
                "Device Type (optional)",
                ["Auto-detect", "Microcontroller", "IC", "Connector", "Module"]
            )
        
        # Extract button
        if st.button("🔍 Extract Pinout Data", type="primary"):
            with st.spinner("🤖 AI is analyzing the pinout diagram..."):
                extracted_data = self.perform_ai_extraction(
                    st.session_state.captured_image,
                    extract_descriptions,
                    extract_functions,
                    device_type
                )
                
                if extracted_data:
                    st.session_state.extracted_data = extracted_data
                    st.success("✅ Pinout data extracted successfully!")
                    
                    # Display results
                    self.display_extraction_results(extracted_data)
                else:
                    st.error("❌ Failed to extract pinout data")
    
    def perform_ai_extraction(self, image_file, include_desc, include_func, device_type):
        """Perform AI extraction using Gemini Vision"""
        try:
            # Prepare the image
            image = Image.open(image_file)
            
            # Create extraction prompt
            prompt = self.create_extraction_prompt(include_desc, include_func, device_type)
            
            # Call Gemini Vision API
            response = st.session_state.gemini_model.generate_content([prompt, image])
            
            # Parse response
            extracted_data = self.parse_ai_response(response.text)
            return extracted_data
            
        except Exception as e:
            st.error(f"Error during AI extraction: {str(e)}")
            return None
    
    def create_extraction_prompt(self, include_desc, include_func, device_type):
        """Create detailed prompt for AI extraction"""
        prompt = """
        Analyze this pinout diagram and extract the pin information in JSON format.
        
        Please provide the data in this exact JSON structure:
        {
            "device_info": {
                "name": "detected device name",
                "package": "detected package type",
                "total_pins": "number of pins"
            },
            "pins": [
                {
                    "pin_number": "pin number",
                    "primary_name": "primary pin name",
                    "alternate_functions": ["function1", "function2", ...],
                    "description": "detailed description if available"
                }
            ]
        }
        
        Instructions:
        1. Identify all visible pins and their numbers
        2. Extract primary pin names/labels
        3. Some Pin names will have a line on top of it, begin the PIn name with # - It represents Active low pin
        """
        
        if include_func:
            prompt += "\n3. Include all alternate functions for each pin"
        
        if include_desc:
            prompt += "\n4. Provide detailed descriptions for each pin function"
        
        if device_type != "Auto-detect":
            prompt += f"\n5. This is a {device_type} pinout diagram"
        
        prompt += """
        
        6. Ensure pin numbers are in correct order
        7. Group related functions together
        8. Use standard abbreviations for common functions (VCC, GND, GPIO, etc.)
        9. Return only valid JSON, no additional text
        """
        
        return prompt
    
    def parse_ai_response(self, response_text):
        """Parse AI response and convert to structured data"""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                return data
            else:
                # Fallback: create structured data from text
                return self.create_fallback_data(response_text)
                
        except json.JSONDecodeError:
            # Fallback parsing
            return self.create_fallback_data(response_text)
    
    def create_fallback_data(self, text):
        """Create fallback structured data if JSON parsing fails"""
        lines = text.split('\n')
        pins = []
        
        for line in lines:
            if 'pin' in line.lower() or any(char.isdigit() for char in line):
                # Simple extraction logic
                parts = line.split()
                if len(parts) >= 2:
                    pins.append({
                        "pin_number": parts[0],
                        "primary_name": parts[1] if len(parts) > 1 else "Unknown",
                        "alternate_functions": parts[2:] if len(parts) > 2 else [],
                        "description": line
                    })
        
        return {
            "device_info": {
                "name": "Unknown Device",
                "package": "Unknown",
                "total_pins": str(len(pins))
            },
            "pins": pins
        }
    
    def display_extraction_results(self, data):
        """Display extracted pinout data"""
        st.subheader("📊 Extraction Results")
        
        # Device info
        if 'device_info' in data:
            device_info = data['device_info']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Device", device_info.get('name', 'Unknown'))
            with col2:
                st.metric("Package", device_info.get('package', 'Unknown'))
            with col3:
                st.metric("Total Pins", device_info.get('total_pins', '0'))
        
        # Pins table
        if 'pins' in data and data['pins']:
            pins_data = []
            for pin in data['pins']:
                pins_data.append({
                    'Pin #': pin.get('pin_number', ''),
                    'Primary Name': pin.get('primary_name', ''),
                    'Alternate Functions': ', '.join(pin.get('alternate_functions', [])),
                    'Description': pin.get('description', '')
                })
            
            df = pd.DataFrame(pins_data)
            st.dataframe(df, use_container_width=True)
            
            # Download options
            self.provide_download_options(df, data)
        else:
            st.warning("No pin data extracted")
    
    def provide_download_options(self, df, raw_data):
        """Provide download options for extracted data"""
        st.subheader("💾 Download Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV download
            csv = df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv,
                file_name=f"pinout_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # JSON download
            json_str = json.dumps(raw_data, indent=2)
            st.download_button(
                label="📋 Download JSON",
                data=json_str,
                file_name=f"pinout_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col3:
            # Excel download
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            
            st.download_button(
                label="📊 Download Excel",
                data=excel_buffer,
                file_name=f"pinout_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def main():
    """Main Streamlit app"""
    st.title("📌 Pinout Diagram Extractor")
    st.markdown("---")
    
    # Initialize extractor
    extractor = PinoutExtractor()
    
    # Initialize session state
    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = 'capture'
    
    # Sidebar navigation
    st.sidebar.title("🔧 Navigation")
    
    # Stage selection
    stage = st.sidebar.radio(
        "Select Stage:",
        ["🎯 Stage 1: Capture", "🤖 Stage 3: Extract"],
        index=0 if st.session_state.current_stage == 'capture' else 1
    )
    
    # Update current stage based on selection
    if "Stage 1" in stage:
        st.session_state.current_stage = 'capture'
    elif "Stage 3" in stage:
        st.session_state.current_stage = 'extract'
    
    # Display current stage info
    st.sidebar.markdown("---")
    st.sidebar.info(f"**Current Stage:** {st.session_state.current_stage.title()}")
    
    # Show captured images in sidebar
    if st.session_state.current_stage == 'extract' and 'captured_image' in st.session_state:
        st.sidebar.markdown("### 📷 Captured Image")
        image = Image.open(st.session_state.captured_image)
        st.sidebar.image(image, use_column_width=True)
    
    # Main content based on stage
    if st.session_state.current_stage == 'capture':
        extractor.capture_screen_area()
    elif st.session_state.current_stage == 'extract':
        extractor.extract_pinout_data()
    
    # Footer
    st.markdown("---")
    st.markdown("**💡 Tips:**")
    st.markdown("- Ensure pinout diagrams are clear and well-lit")
    st.markdown("- Higher resolution images produce better results")
    st.markdown("- Make sure pin numbers and labels are visible")

if __name__ == "__main__":
    main()