import streamlit as st
import requests
import time
from datetime import datetime

# --- Configuration ---
st.set_page_config(
    page_title="Exam Paper Processor",
    page_icon="📝",
    layout="centered"
)

# Constants
WEBHOOK_URL = st.secrets.get("WEBHOOK_URL", "https://n8n-wa-5axz.onrender.com/webhook/process-notes")
MAX_FILE_SIZE_MB = 10

# --- State Management ---
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result' not in st.session_state:
    st.session_state.result = None

# --- Helper Functions ---
def process_document(file_obj):
    """
    Sends the file to the webhook and returns the result or error.
    """
    try:
        # Prepare file for upload
        file_bytes = file_obj.read()
        file_obj.seek(0) # Reset pointer
        
        files = {
            "file": (file_obj.name, file_bytes, "application/pdf")
        }
        
        # Send request
        response = requests.post(WEBHOOK_URL, files=files, timeout=240)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.content,
                "filename": file_obj.name.replace(".pdf", ".docx")
            }
        else:
            return {
                "success": False,
                "error": f"Server returned status {response.status_code}: {response.text}"
            }
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "The request timed out. The file might be too complex."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection error. Please check your internet or the server status."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def reset_app():
    """Resets the session state to allow processing a new file."""
    st.session_state.result = None
    st.session_state.processing = False
    # We do NOT rerun here immediately to avoid UI glitches, 
    # the main loop handles the update.

# --- Sidebar ---
with st.sidebar:
    st.header("📌 Instructions")
    st.info(
        """
        1. Upload your handwritten exam PDF.
        2. Click **Process Exam Paper**.
        3. Wait for the AI to convert it (approx. 1-3 mins).
        4. Download the formatted Word doc.
        """
    )
    st.markdown("---")
    st.caption(f"Max file size: {MAX_FILE_SIZE_MB} MB")

# --- Main Interface ---
st.title("📝 Exam Paper Processor")
st.markdown("##### Convert handwritten exam papers $\\rightarrow$ formatted Word documents")
st.markdown("---")

# 1. File Upload Section
if st.session_state.result is None:
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        disabled=st.session_state.processing,
        help="Ensure the scan is clear for best results."
    )

    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"❌ File size ({file_size_mb:.2f} MB) exceeds the {MAX_FILE_SIZE_MB} MB limit.")
        else:
            # Centered Process Button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                process_btn = st.button(
                    "🚀 Process Exam Paper", 
                    disabled=st.session_state.processing, 
                    use_container_width=True,
                    type="primary"
                )

            if process_btn:
                st.session_state.processing = True
                st.rerun()

# 2. Processing Logic (Runs if state is True)
if st.session_state.processing and uploaded_file:
    
    # This acts as the "Loading Buffer"
    with st.status("🤖 AI is working on your document...", expanded=True) as status:
        st.write("📤 Uploading file to server...")
        time.sleep(1) # Visual padding
        
        st.write("🧠 Analyzing handwriting and structure...")
        
        # The actual blocking call happens here inside the spinner context
        result = process_document(uploaded_file)
        
        if result["success"]:
            st.write("✅ Formatting document...")
            time.sleep(0.5)
            status.update(label="Processing Complete!", state="complete", expanded=False)
            
            # Save to session state
            st.session_state.result = {
                "fileName": result["filename"],
                "docxData": result["data"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.processing = False
            st.toast("Document generated successfully!", icon="🎉")
            st.rerun()
            
        else:
            status.update(label="Processing Failed", state="error", expanded=False)
            st.error(f"❌ Error: {result['error']}")
            st.session_state.processing = False

# 3. Result Display Section
if st.session_state.result is not None:
    st.success("✅ Document Ready for Download")
    
    res = st.session_state.result
    
    # Metadata Card
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**📄 File:** `{res['fileName']}`")
        with c2:
            st.write(f"**🕒 Time:** {res['timestamp'].split(' ')[1]}")

    # Action Buttons
    col_dl, col_reset = st.columns([1, 1])
    
    with col_dl:
        st.download_button(
            label="⬇️ Download Word Doc",
            data=res["docxData"],
            file_name=res["fileName"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary"
        )
    
    with col_reset:
        if st.button("🔄 Process Another File", use_container_width=True):
            reset_app()
            st.rerun()

# Footer
st.markdown("---")
st.caption("Powered by **Gemini** + **n8n Automation**")