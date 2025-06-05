import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
import io
import json
from typing import List, Dict

# Page configuration
st.set_page_config(
    page_title="SymbolGen GPT",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'document_content' not in st.session_state:
    st.session_state.document_content = ""
if 'gemini_model' not in st.session_state:
    st.session_state.gemini_model = None

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

# Main App Layout
st.title("📄 SymbolGen GPT")
st.markdown("Upload a Renesas datasheet and ask questions about its content!")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key input
    api_key = st.text_input("Gemini API Key", type="password", key="api_key")
    if api_key and not st.session_state.gemini_model:
        if setup_gemini(api_key):
            st.success("✅ Gemini API configured!")
    
    st.divider()
    
    # Document upload
    st.header("📤 Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'txt'],
        help="Upload PDF, DOCX, or TXT files"
    )
    
    if uploaded_file:
        with st.spinner("Processing document..."):
            document_text = process_document(uploaded_file)
            if document_text:
                st.session_state.document_content = document_text
                st.success(f"✅ Document processed! ({len(document_text)} characters)")
                
                # Show document preview
                with st.expander("📄 Document Preview"):
                    st.text_area("Content preview:", document_text[:500] + "...", height=200, disabled=True)
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    st.header("💬 Upload Renesas Datasheet")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if question := st.chat_input("Ask a question about your document..."):
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
                with st.spinner("Thinking..."):
                    response = get_ai_response(question, st.session_state.document_content)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# with col2:
#     st.header("📊 Stats")
#     if st.session_state.document_content:
#         st.metric("Document Length", f"{len(st.session_state.document_content):,} chars")
#         st.metric("Words", f"{len(st.session_state.document_content.split()):,}")
#         st.metric("Chat Messages", len(st.session_state.messages))
#     else:
#         st.info("Upload a Datasheet to see stats")

# Footer
st.divider()

