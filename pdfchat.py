import os
#this is the correct code for pdf chat 
import streamlit as st
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import google.generativeai as genai
import random
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Set up the model
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 40,
    "max_output_tokens": 4096,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    safety_settings=safety_settings,
)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    text = ""
    pdf_reader = PdfReader(pdf_file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to upload file to Gemini
def upload_to_gemini(file_path, mime_type):
    """Uploads the file to Gemini and returns the file object."""
    try:
        file = genai.upload_file(file_path, mime_type=mime_type)
        return file
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None

# Function to wait for file processing
def wait_for_files_active(files):
    """Waits for files to be ready for use after uploading."""
    for file in files:
        while file.state.name == "PROCESSING":
            time.sleep(5)
            file = genai.get_file(file.name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process.")

# Human-like responses
greeting_responses = [
    "Hello! I'm ready to analyze your PDF. What would you like to know?",
    "Hi there! I've processed your document and I'm here to help.",
    "Good {time_of_day}! Let's explore your PDF together."
]

redirect_responses = [
    "I'm focused on this PDF. What would you like to know about it?",
    "Let's discuss the document. What information are you looking for?",
    "I'd be happy to answer questions about this PDF specifically."
]

# Initialize session state
if "pdf_chat" not in st.session_state:
    st.session_state.pdf_chat = {
        "messages": [],
        "file_processed": False,
        "gemini_file": None,
        "chat_session": None
    }

# Streamlit UI
st.title("📄 Enhanced PDF Chat Assistant")
st.caption("Upload a PDF and have a natural conversation about its contents")

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

# Handle PDF upload and processing
if uploaded_file and not st.session_state.pdf_chat["file_processed"]:
    with st.spinner("Processing your PDF..."):
        try:
            # Save uploaded file temporarily
            temp_path = "temp_upload.pdf"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Upload to Gemini
            st.session_state.pdf_chat["gemini_file"] = upload_to_gemini(temp_path, "application/pdf")
            wait_for_files_active([st.session_state.pdf_chat["gemini_file"]])
            
            # Initialize chat session
            st.session_state.pdf_chat["chat_session"] = model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [
                        st.session_state.pdf_chat["gemini_file"],
                        "You are a PDF analysis assistant. Provide accurate answers "
                        "strictly based on the document content. Be professional yet friendly. "
                        "If information isn't in the document, say so. For irrelevant questions, "
                        "gently redirect to PDF content."
                    ]
                }
            ])
            
            st.session_state.pdf_chat["file_processed"] = True
            st.session_state.pdf_chat["messages"].append({
                "role": "assistant",
                "content": random.choice(greeting_responses).format(
                    time_of_day="morning" if datetime.now().hour < 12 else "afternoon"
                )
            })
            st.rerun()
            
        except Exception as e:
            st.error(f"Error processing PDF: {e}")

# Display chat messages
for msg in st.session_state.pdf_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle user input
if prompt := st.chat_input("Ask about the PDF..."):
    if not st.session_state.pdf_chat["file_processed"]:
        st.warning("Please upload a PDF file first")
        st.stop()
    
    # Add user message to history
    st.session_state.pdf_chat["messages"].append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                response = st.session_state.pdf_chat["chat_session"].send_message(prompt)
                response_text = response.text
                
                # Fallback if empty response
                if not response_text.strip():
                    response_text = "I couldn't find relevant information in the document about that."
                
            except Exception as e:
                response_text = f"An error occurred: {str(e)}"
            
            st.markdown(response_text)
    
    # Add assistant response to history
    st.session_state.pdf_chat["messages"].append({"role": "assistant", "content": response_text})

# Add clear conversation button
if st.session_state.pdf_chat["messages"]:
    if st.button("Clear Conversation"):
        st.session_state.pdf_chat["messages"] = []
        st.rerun()
