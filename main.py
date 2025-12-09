import streamlit as st
import requests
import time

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Exam Paper Processor",
    page_icon="📝",
    layout="centered"
)

# Constants
WEBHOOK_URL = st.secrets.get("WEBHOOK_URL", "https://n8n-wa-5axz.onrender.com/webhook/process-notes")
DRIVE_FOLDER_LINK = "https://drive.google.com/drive/folders/19F1zlmuVdSs-KyqUkYT6jgUhr96OlLt-?usp=sharing"
MAX_FILE_SIZE_MB = 10

# --- State Initialization ---
if "processing" not in st.session_state:
    st.session_state.processing = False
if "upload_success" not in st.session_state:
    st.session_state.upload_success = False
if "file_processed" not in st.session_state:
    st.session_state.file_processed = False  # NEW: Track if file was already sent

# --- Helper: Send File to Webhook ---
def process_document(file_obj):
    try:
        file_bytes = file_obj.read()
        files = {"file": (file_obj.name, file_bytes, "application/pdf")}

        # We keep the timeout to allow n8n time to receive and acknowledge
        response = requests.post(WEBHOOK_URL, files=files, timeout=240)

        # We only care if the server accepted the request (200 OK)
        if response.status_code == 200:
            return {"success": True}
        else:
            return {
                "success": False,
                "error": f"Server returned {response.status_code}: {response.text}"
            }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "The request timed out. The file might be processing in the background."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection error. Check your internet/server."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def reset_app():
    """Properly reset all state variables"""
    st.session_state.processing = False
    st.session_state.upload_success = False
    st.session_state.file_processed = False  # IMPORTANT: Reset this flag
    if "uploaded_file" in st.session_state:
        del st.session_state.uploaded_file
    st.rerun()  # Force immediate rerun with clean state

# --- Sidebar: Instructions ---
with st.sidebar:
    st.header("📌 Instructions")
    st.info(
        f"""
        1️⃣ Upload your handwritten exam PDF  
        2️⃣ Click **Upload & Process**  
        3️⃣ Wait for the success message  
        4️⃣ Check the Google Drive folder:  
        [Open Google Drive Folder]({DRIVE_FOLDER_LINK})
        
        - To access Google drive folder you must be logged into the Symbiosis Google account.
        - Refresh the app if it gets stuck.
        - Call me if you face any issues!
        """
    )
    st.divider()
    st.caption(f"📎 Max file size: {MAX_FILE_SIZE_MB} MB")

# --- Main UI ---
st.title("📝 Exam Paper Processor")
st.write("Upload exam papers to generate formatted Word docs in Google Drive.")
st.divider()

# ======================
# 1️⃣ File Upload
# ======================
if not st.session_state.upload_success and not st.session_state.processing:
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], key="file_uploader")

    if uploaded_file:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"❌ File size ({file_size_mb:.2f} MB) exceeds {MAX_FILE_SIZE_MB} MB limit.")
        else:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                # Button is disabled if already processing
                button_disabled = st.session_state.processing or st.session_state.file_processed
                
                if st.button(
                    "🚀 Upload & Process", 
                    type="primary", 
                    use_container_width=True,
                    disabled=button_disabled,  # Disable button when processing
                    key="process_button"
                ):
                    st.session_state.processing = True
                    st.session_state.uploaded_file = uploaded_file
                    st.session_state.file_processed = False  # Mark as not yet processed
                    st.rerun()  # Rerun to show processing state
                
                # Show status message when disabled
                if button_disabled:
                    st.info("⏳ Processing in progress...")

# ======================
# 2️⃣ Processing (Single Execution with Guard)
# ======================
if (st.session_state.processing and 
    "uploaded_file" in st.session_state and 
    not st.session_state.file_processed):  # GUARD: Only process if not already done
    
    with st.status("🤖 Sending file to processor...", expanded=True) as status:
        st.write("📤 Uploading PDF...")
        
        result = process_document(st.session_state.uploaded_file)
        
        # Mark as processed IMMEDIATELY after sending
        st.session_state.file_processed = True

        if result["success"]:
            st.write("✅ File accepted by server!")
            time.sleep(1)
            status.update(label="Sent!", state="complete")
            st.session_state.upload_success = True
            st.session_state.processing = False
            st.toast("🎉 Upload Successful!")
            st.rerun()  # Rerun to show success screen
        else:
            status.update(label="Failed ❌", state="error")
            st.error(result["error"])
            st.session_state.processing = False
            st.session_state.file_processed = False  # Allow retry on failure

# ======================
# 3️⃣ Success Screen
# ======================
if st.session_state.upload_success:
    st.success("🎯 File successfully sent for processing!")
    
    st.markdown(
        f"""
        ### What happens next?
        The AI is converting your file. It will appear in the shared folder automatically in 2-3 minutes.
        
        👉 **[Click here to open Google Drive Folder]({DRIVE_FOLDER_LINK})**
        """
    )
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Process Another File", type="primary", use_container_width=True):
            reset_app()  # This now properly resets everything

# Footer
st.divider()
st.caption("✨ Powered by **Gemini AI** + **n8n automation**")