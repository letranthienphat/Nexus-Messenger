import streamlit as st
import json
from github import Github
from github import GithubException
from datetime import datetime

# Cấu hình giao diện và tiêu đề ứng dụng
st.set_page_config(page_title="Nexus Messenger", page_icon="💬", layout="centered")
st.title("💬 Nexus Messenger")

# --- KẾT NỐI VÀ KIỂM TRA CẤU HÌNH GITHUB (ĐÃ ĐỔI THEO TIỀN TỐ DB_) ---
try:
    GITHUB_TOKEN = st.secrets["DB_GITHUB_TOKEN"]
    REPO_NAME = st.secrets["DB_REPO_NAME"]
    BRANCH = st.secrets.get("DB_BRANCH", "main")
    FILE_PATH = "data.json"
except Exception:
    st.error("⚠️ Thiếu cấu hình Secrets! Vui lòng kiểm tra lại cấu hình DB_GITHUB_TOKEN và DB_REPO_NAME trong Advanced Settings của Streamlit Cloud.")
    st.stop()

# Khởi tạo kết nối tới GitHub API
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# --- CÁC HÀM XỬ LÝ DỮ LIỆU JSON TRÊN GITHUB ---
def load_chat_history():
    """Tải lịch sử tin nhắn từ file data.json trên kho lưu trữ GitHub"""
    try:
        file_content = repo.get_contents(FILE_PATH, ref=BRANCH)
        data = json.loads(file_content.decoded_content.decode("utf-8"))
        return data, file_content.sha
    except GithubException as e:
        if e.status == 404:
            return [], None
        else:
            st.error(f"Lỗi kết nối GitHub API: {e.data.get('message')}")
            return [], None

def save_chat_history(new_history, sha=None):
    """Ghi đè hoặc tạo mới dữ liệu lịch sử chat lên file data.json của GitHub"""
    content_str = json.dumps(new_history, ensure_ascii=False, indent=4)
    commit_message = f"Nexus Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        if sha:
            repo.update_file(FILE_PATH, commit_message, content_str, sha, branch=BRANCH)
        else:
            repo.create_file(FILE_PATH, commit_message, content_str, branch=BRANCH)
        return True
    except Exception as e:
        st.error(f"Lỗi khi đồng bộ dữ liệu lên GitHub: {e}")
        return False

# --- XỬ LÝ GIAO DIỆN VÀ HỘI THOẠI ---

chat_history, file_sha = load_chat_history()

st.sidebar.header("Cài đặt tài khoản")
user_name = st.sidebar.text_input("Tên hiển thị của bạn:", value="User").strip()
if not user_name:
    user_name = "User"

st.sidebar.write("---")
if st.sidebar.button("🗑️ Xóa lịch sử hội thoại"):
    if save_chat_history([], file_sha):
        st.success("Đã xóa lịch sử thành công!")
        st.rerun()

st.write("### Hộp thư chung")
for msg in chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['user']}** <span style='color:gray; font-size:12px;'>• {msg['time']}</span>", unsafe_allow_html=True)
        st.write(msg["text"])

if prompt := st.chat_input("Nhập tin nhắn của bạn..."):
    with st.chat_message("user"):
        st.markdown(f"**{user_name}** <span style='color:gray; font-size:12px;'>• Vừa xong</span>", unsafe_allow_html=True)
        st.write(prompt)
        
    new_message = {
        "user": user_name,
        "role": "user",
        "time": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        "text": prompt
    }
    
    chat_history.append(new_message)
    if save_chat_history(chat_history, file_sha):
        st.rerun()
