import streamlit as st
import json
import hashlib
import base64
from github import Github
from github import GithubException
from datetime import datetime

# Cấu hình giao diện và tiêu đề ứng dụng
st.set_page_config(page_title="Nexus Messenger", page_icon="💬", layout="centered")
st.title("💬 Nexus Messenger")

# --- KẾT NỐI VÀ KIỂM TRA CẤU HÌNH GITHUB ---
try:
    GITHUB_TOKEN = st.secrets["DB_GITHUB_TOKEN"]
    REPO_NAME = st.secrets["DB_REPO_NAME"]
    BRANCH = st.secrets.get("DB_BRANCH", "main")
    CHAT_FILE = "data.json"
    USER_FILE = "accounts.json"
except Exception:
    st.error("⚠️ Thiếu cấu hình Secrets! Vui lòng kiểm tra lại cấu hình DB_GITHUB_TOKEN và DB_REPO_NAME trong Advanced Settings của Streamlit Cloud.")
    st.stop()

# Khởi tạo kết nối tới GitHub API
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# --- CÁC HÀM XỬ LÝ DỮ LIỆU TỪ GITHUB ---
def load_github_file(file_path):
    """Tải nội dung file JSON từ GitHub"""
    try:
        file_content = repo.get_contents(file_path, ref=BRANCH)
        data = json.loads(file_content.decoded_content.decode("utf-8"))
        return data, file_content.sha
    except GithubException as e:
        if e.status == 404:
            return [], None
        else:
            st.error(f"Lỗi kết nối GitHub ({file_path}): {e.data.get('message')}")
            return [], None

def save_github_file(file_path, data, sha=None, message="Update"):
    """Ghi dữ liệu JSON lên GitHub"""
    content_str = json.dumps(data, ensure_ascii=False, indent=4)
    try:
        if sha:
            repo.update_file(file_path, message, content_str, sha, branch=BRANCH)
        else:
            repo.create_file(file_path, message, content_str, branch=BRANCH)
        return True
    except Exception as e:
        st.error(f"Lỗi khi đồng bộ dữ liệu lên GitHub ({file_path}): {e}")
        return False

def upload_binary_file(file_name, file_bytes):
    """Tải file nhị phân (hình ảnh, tài liệu) lên thư mục uploads/ trên GitHub"""
    github_path = f"uploads/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_name}"
    commit_message = f"Upload file: {file_name}"
    try:
        repo.create_file(github_path, commit_message, file_bytes, branch=BRANCH)
        # Trả về URL trực tiếp dẫn tới file trên kho lưu trữ của bạn
        return f"https://github.com/{REPO_NAME}/blob/{BRANCH}/{github_path}?raw=true"
    except Exception as e:
        st.error(f"Lỗi tải file lên GitHub: {e}")
        return None

def hash_password(password):
    """Mã hóa mật khẩu để bảo mật dữ liệu lưu trên GitHub"""
    return hashlib.sha256(password.encode()).hexdigest()

# --- KHỞI TẠO STATE BAN ĐẦU ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- HỆ THỐNG ĐĂNG NHẬP / ĐĂNG KÝ ---
if not st.session_state.logged_in:
    st.subheader("Vui lòng đăng nhập hoặc đăng ký để tiếp tục")
    tab_login, tab_register = st.tabs(["🔑 Đăng nhập", "📝 Đăng ký"])
    accounts, user_sha = load_github_file(USER_FILE)
    
    with tab_login:
        login_user = st.text_input("Tên đăng nhập:", key="login_user_input").strip()
        login_pass = st.text_input("Mật khẩu:", type="password", key="login_pass_input")
        
        if st.button("Đăng nhập", use_container_width=True):
            if not login_user or not login_pass:
                st.warning("Vui lòng nhập đầy đủ thông tin.")
            else:
                hashed = hash_password(login_pass)
                user_found = next((u for u in accounts if u["username"] == login_user and u["password"] == hashed), None)
                if user_found:
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu!")
                    
    with tab_register:
        reg_user = st.text_input("Tên đăng nhập mới:", key="reg_user_input").strip()
        reg_pass = st.text_input("Mật khẩu mới:", type="password", key="reg_pass_input")
        reg_confirm = st.text_input("Xác nhận mật khẩu:", type="password", key="reg_confirm_input")
        
        if st.button("Đăng ký tài khoản", use_container_width=True):
            if not reg_user or not reg_pass:
                st.warning("Vui lòng điền đầy đủ các trường thông tin.")
            elif reg_pass != reg_confirm:
                st.error("Mật khẩu xác nhận không trùng khớp!")
            elif any(u["username"] == reg_user for u in accounts):
                st.error("Tên đăng nhập này đã tồn tại trên hệ thống!")
            else:
                new_account = {
                    "username": reg_user, 
                    "password": hash_password(reg_pass),
                    "friends": [],
                    "friend_requests_received": [],
                    "friend_requests_sent": []
                }
                accounts.append(new_account)
                if save_github_file(USER_FILE, accounts, user_sha, message=f"New user registered: {reg_user}"):
                    st.success("Đăng ký thành công! Hãy chuyển sang tab Đăng nhập.")
    st.stop()

# --- GIAO DIỆN CHAT VÀ QUẢN LÝ BẠN BÈ (SAU KHI ĐĂNG NHẬP) ---

# Tải cấu trúc tài khoản và lịch sử tin nhắn mới nhất
accounts, user_sha = load_github_file(USER_FILE)
chat_history, chat_sha = load_github_file(CHAT_FILE)

# Lấy thông tin tài khoản hiện tại trong DB
current_user_data = next((u for u in accounts if u["username"] == st.session_state.username), None)
if not current_user_data:
    st.error("Lỗi dữ liệu tài khoản.")
    st.stop()

# Khởi tạo các khóa bạn bè nếu tài khoản cũ chưa có
if "friends" not in current_user_data: current_user_data["friends"] = []
if "friend_requests_received" not in current_user_data: current_user_data["friend_requests_received"] = []
if "friend_requests_sent" not in current_user_data: current_user_data["friend_requests_sent"] = []

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN & BẠN BÈ ---
st.sidebar.markdown(f"### 👤 Tài khoản: **{st.session_state.username}**")
if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.sidebar.write("---")

# 1. Tính năng Kết bạn (Gửi yêu cầu)
st.sidebar.subheader("🤝 Kết bạn mới")
friend_target = st.sidebar.text_input("Nhập tên người dùng khác:", key="friend_target_input").strip()
if st.sidebar.button("Gửi yêu cầu kết bạn", use_container_width=True):
    target_user_data = next((u for u in accounts if u["username"] == friend_target), None)
    
    if not friend_target:
        st.sidebar.warning("Vui lòng nhập tên người dùng.")
    elif friend_target == st.session_state.username:
        st.sidebar.error("Bạn không thể kết bạn với chính mình!")
    elif not target_user_data:
        st.sidebar.error("Không tìm thấy người dùng này trên hệ thống!")
    elif friend_target in current_user_data.get("friends", []):
        st.sidebar.info("Hai người đã là bạn bè từ trước.")
    elif friend_target in current_user_data.get("friend_requests_sent", []):
        st.sidebar.info("Bạn đã gửi yêu cầu cho người này rồi.")
    else:
        # Thêm vào mảng gửi/nhận của đôi bên
        current_user_data.setdefault("friend_requests_sent", []).append(friend_target)
        target_user_data.setdefault("friend_requests_received", []).append(st.session_state.username)
        if save_github_file(USER_FILE, accounts, user_sha, message=f"{st.session_state.username} sent friend request to {friend_target}"):
            st.sidebar.success(f"Đã gửi yêu cầu kết bạn đến {friend_target}!")
            st.rerun()

# 2. Quản lý yêu cầu kết bạn đến
req_received = current_user_data.get("friend_requests_received", [])
if req_received:
    st.sidebar.subheader("📥 Yêu cầu kết bạn chờ duyệt")
    for sender in req_received:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button(f"✅ Nhận {sender}", key=f"acc_{sender}"):
                # Đồng ý kết bạn: cập nhật danh sách bạn bè, xóa yêu cầu chờ
                current_user_data.setdefault("friends", []).append(sender)
                current_user_data["friend_requests_received"].remove(sender)
                
                sender_data = next((u for u in accounts if u["username"] == sender), None)
                if sender_data:
                    sender_data.setdefault("friends", []).append(st.session_state.username)
                    if st.session_state.username in sender_data.get("friend_requests_sent", []):
                        sender_data["friend_requests_sent"].remove(st.session_state.username)
                
                if save_github_file(USER_FILE, accounts, user_sha, message=f"{st.session_state.username} accepted friend request from {sender}"):
                    st.rerun()
        with col2:
            if st.button(f"❌ Từ chối {sender}", key=f"dec_{sender}"):
                current_user_data["friend_requests_received"].remove(sender)
                sender_data = next((u for u in accounts if u["username"] == sender), None)
                if sender_data and st.session_state.username in sender_data.get("friend_requests_sent", []):
                    sender_data["friend_requests_sent"].remove(st.session_state.username)
                
                if save_github_file(USER_FILE, accounts, user_sha, message=f"{st.session_state.username} declined request from {sender}"):
                    st.rerun()

# 3. Chọn Bạn bè để chat công khai/riêng tư
st.sidebar.write("---")
st.sidebar.subheader("💬 Chọn phòng chat")
my_friends = current_user_data.get("friends", [])

# Danh sách phòng gồm Hộp thư chung và danh sách từng người bạn
chat_options = ["Hộp thư chung (Chỉ bạn bè mới đọc/ghi)"] + my_friends
selected_chat = st.sidebar.selectbox("Trò chuyện với:", chat_options)

# Nút Xóa lịch sử (Chỉ áp dụng với Hộp thư chung)
if selected_chat == "Hộp thư chung (Chỉ bạn bè mới đọc/ghi)":
    if st.sidebar.button("🗑️ Xóa lịch sử Hộp thư chung", use_container_width=True):
        if save_github_file(CHAT_FILE, [], chat_sha, message="Clear chat history"):
            st.success("Đã xóa lịch sử thành công!")
            st.rerun()

# --- GIAO DIỆN HIỂN THỊ TIN NHẮN ---
st.write(f"### {selected_chat}")

# Lọc tin nhắn hiển thị
# - Nếu là Hộp thư chung: Chỉ hiển thị nếu người gửi là bạn bè hoặc chính mình
# - Nếu là chat 1-1 với bạn: Chỉ hiển thị tin nhắn riêng giữa 2 người
filtered_chats = []
for msg in chat_history:
    if selected_chat == "Hộp thư chung (Chỉ bạn bè mới đọc/ghi)":
        if msg.get("room", "public") == "public":
            if msg["user"] == st.session_state.username or msg["user"] in my_friends:
                filtered_chats.append(msg)
    else:
        if msg.get("room") == "private":
            # Tin nhắn giữa User A và User B
            if (msg["user"] == st.session_state.username and msg.get("to") == selected_chat) or \
               (msg["user"] == selected_chat and msg.get("to") == st.session_state.username):
                filtered_chats.append(msg)

for msg in filtered_chats:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['user']}** <span style='color:gray; font-size:12px;'>• {msg['time']}</span>", unsafe_allow_html=True)
        # Kiểm tra xem tin nhắn có chứa file đính kèm không
        if "file_url" in msg:
            if msg["text"]: 
                st.write(msg["text"])
            st.markdown(f"📂 **File đính kèm:** [{msg['file_name']}]({msg['file_url']})")
        else:
            st.write(msg["text"])

# --- HỆ THỐNG GỬI TIN NHẮN VÀ TẢI LÊN FILE ---

# Kiểm tra điều kiện chat phòng riêng 1-1 (Đảm bảo vẫn là bạn bè)
is_still_friend = True
if selected_chat != "Hộp thư chung (Chỉ bạn bè mới đọc/ghi)" and selected_chat not in my_friends:
    is_still_friend = False
    st.error("Bạn không thể nhắn tin do người này chưa kết bạn hoặc đã hủy kết bạn với bạn.")

if is_still_friend:
    # 1. Tính năng đính kèm tệp tin (Tối đa 25MB)
    uploaded_file = st.file_uploader("Đính kèm file (Dưới 25MB):", type=None)
    file_url = None
    file_name = None
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        
        if file_size_mb > 25.0:
            st.error(f"❌ Kích thước file của bạn là {file_size_mb:.2f}MB, vượt quá giới hạn 25MB của GitHub!")
            uploaded_file = None
        else:
            file_name = uploaded_file.name
            st.info(f"📁 Chuẩn bị tải lên: {file_name} ({file_size_mb:.2f} MB)")

    # 2. Khung nhập tin nhắn chữ
    if prompt := st.chat_input("Nhập nội dung tin nhắn..."):
        # Nếu có chọn file, tiến hành upload lên GitHub trước để lấy URL trực tiếp
        if uploaded_file is not None:
            with st.spinner("Đang tải file lên GitHub..."):
                file_url = upload_binary_file(file_name, file_bytes)
        
        # Tạo gói tin nhắn
        new_message = {
            "user": st.session_state.username,
            "role": "user",
            "time": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "text": prompt,
            "room": "public" if selected_chat == "Hộp thư chung (Chỉ bạn bè mới đọc/ghi)" else "private"
        }
        
        # Nếu là chat riêng, chỉ định người nhận
        if selected_chat != "Hộp thư chung (Chỉ bạn bè mới đọc/ghi)":
            new_message["to"] = selected_chat
            
        # Nếu có file đi kèm, bổ sung thông tin file vào JSON chat
        if file_url:
            new_message["file_url"] = file_url
            new_message["file_name"] = file_name
            
        chat_history.append(new_message)
        if save_github_file(CHAT_FILE, chat_history, chat_sha, message=f"Message from {st.session_state.username}"):
            st.rerun()
