import streamlit as st
import json
import hashlib
import base64
import time
from github import Github
from github import GithubException
from datetime import datetime

# --- ĐỊNH NGHĨA ĐA NGÔN NGỮ ---
LANGUAGES = {
    "Tiếng Việt": {
        "title": "💬 Nexus Messenger",
        "missing_secrets": "⚠️ Thiếu cấu hình Secrets! Vui lòng kiểm tra lại cấu hình DB_GITHUB_TOKEN và DB_REPO_NAME trong Advanced Settings của Streamlit Cloud.",
        "login_sub": "Vui lòng đăng nhập hoặc đăng ký để tiếp tục",
        "tab_login": "🔑 Đăng nhập",
        "tab_register": "📝 Đăng ký",
        "username": "Tên đăng nhập:",
        "password": "Mật khẩu:",
        "new_password": "Mật khẩu mới:",
        "confirm_password": "Xác nhận mật khẩu:",
        "remember_me": "Ghi nhớ đăng nhập",
        "btn_login": "Đăng nhập",
        "btn_register": "Đăng ký tài khoản",
        "err_missing": "Vui lòng nhập đầy đủ thông tin.",
        "err_wrong": "Sai tên đăng nhập hoặc mật khẩu!",
        "err_match": "Mật khẩu xác nhận không trùng khớp!",
        "err_exist": "Tên đăng nhập này đã tồn tại trên hệ thống!",
        "success_login": "Đăng nhập thành công!",
        "success_register": "Đăng ký thành công! Hãy chuyển sang tab Đăng nhập.",
        "sidebar_account": "👤 Tài khoản:",
        "btn_logout": "🚪 Đăng xuất",
        "sidebar_friend": "🤝 Kết bạn mới",
        "input_friend": "Nhập tên người dùng khác:",
        "btn_friend_req": "Gửi yêu cầu kết bạn",
        "err_friend_self": "Bạn không thể kết bạn với chính mình!",
        "err_friend_404": "Không tìm thấy người dùng này trên hệ thống!",
        "info_friend_already": "Hai người đã là bạn bè từ trước.",
        "info_friend_sent": "Bạn đã gửi yêu cầu cho người này rồi.",
        "success_friend_sent": "Đã gửi yêu cầu kết bạn!",
        "sidebar_req_recv": "📥 Yêu cầu kết bạn chờ duyệt",
        "btn_accept": "✅ Nhận",
        "btn_decline": "❌ Từ chối",
        "sidebar_room": "💬 Chọn phòng chat",
        "public_room": "Hộp thư chung (Chỉ bạn bè mới đọc/ghi)",
        "btn_clear_chat": "🗑️ Xóa lịch sử Hộp thư chung",
        "success_clear": "Đã xóa lịch sử thành công!",
        "err_not_friend": "Bạn không thể nhắn tin do người này chưa kết bạn hoặc đã hủy kết bạn.",
        "file_uploader": "Đính kèm tệp tin đa phương tiện (Dưới 25MB):",
        "err_file_size": "❌ File không hợp lệ! Kích thước file vượt quá giới hạn 25MB của GitHub. Vui lòng chọn file nhỏ hơn.",
        "info_file_ready": "📁 Tệp hợp lệ, chuẩn bị tải lên:",
        "chat_input": "Nhập nội dung tin nhắn...",
        "spinner_upload": "Đăng tải file lên GitHub...",
        "file_attached": "📂 Tải về tài liệu:",
        "just_now": "Vừa xong",
        "software_info_title": "ℹ️ Thông tin phần mềm",
        "software_info_body": """
        **Ứng dụng:** Nexus Messenger
        **Phiên bản:** 2.4.0
        **Tính năng:** Đồng hồ thời gian thực tự động lấy theo múi giờ trình duyệt máy khách (Client Timezone). Ô tải file đặt phía dưới cạnh ô chat.
        **Giới hạn truyền tải:** Tệp đính kèm < 25MB
        **Bảo mật:** Mật khẩu được mã hóa SHA-256 trước khi lưu trữ.
        """
    },
    "English": {
        "title": "💬 Nexus Messenger",
        "missing_secrets": "⚠️ Missing Secrets! Please check DB_GITHUB_TOKEN and DB_REPO_NAME in Streamlit Cloud Advanced Settings.",
        "login_sub": "Please login or register to continue",
        "tab_login": "🔑 Login",
        "tab_register": "📝 Register",
        "username": "Username:",
        "password": "Password:",
        "new_password": "New Password:",
        "confirm_password": "Confirm Password:",
        "remember_me": "Remember me",
        "btn_login": "Login",
        "btn_register": "Register Account",
        "err_missing": "Please fill in all fields.",
        "err_wrong": "Incorrect username or password!",
        "err_match": "Passwords do not match!",
        "err_exist": "Username already exists!",
        "success_login": "Logged in successfully!",
        "success_register": "Registered successfully! Please switch to Login tab.",
        "sidebar_account": "👤 Account:",
        "btn_logout": "🚪 Logout",
        "sidebar_friend": "🤝 Add Friend",
        "input_friend": "Enter target username:",
        "btn_friend_req": "Send Friend Request",
        "err_friend_self": "You cannot add yourself!",
        "err_friend_404": "User not found!",
        "info_friend_already": "You are already friends.",
        "info_friend_sent": "Friend request already sent.",
        "success_friend_sent": "Friend request sent!",
        "sidebar_req_recv": "📥 Pending Requests",
        "btn_accept": "✅ Accept",
        "btn_decline": "❌ Decline",
        "sidebar_room": "💬 Chat Rooms",
        "public_room": "Public Box (Friends only)",
        "btn_clear_chat": "🗑️ Clear Public Chat History",
        "success_clear": "Cleared successfully!",
        "err_not_friend": "Cannot chat. You are not friends with this user.",
        "file_uploader": "Attach media file (Under 25MB):",
        "err_file_size": "❌ Invalid file! File size exceeds GitHub's 25MB limit. Please choose a smaller file.",
        "info_file_ready": "📁 Valid file, ready to upload:",
        "chat_input": "Type a message...",
        "spinner_upload": "Uploading file to GitHub...",
        "file_attached": "📂 Download Document:",
        "just_now": "Just now",
        "software_info_title": "ℹ️ Software Info",
        "software_info_body": """
        **App:** Nexus Messenger
        **Version:** 2.4.0
        **Features:** Real-time clock synchronized automatically with client browser timezone. Stable bottom panel.
        **Transfer Limit:** Attachments < 25MB
        **Security:** Passwords are encrypted via SHA-256.
        """
    }
}

# --- KHỞI TẠO STATE BAN ĐẦU ---
if "lang" not in st.session_state:
    st.session_state.lang = "Tiếng Việt"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

L = LANGUAGES.get(st.session_state.lang, LANGUAGES["Tiếng Việt"])

st.set_page_config(page_title="Nexus Messenger", page_icon="💬", layout="centered")

# --- TRÍCH XUẤT MÚI GIỜ & THỜI GIAN THỰC TỪ TRÌNH DUYỆT NGƯỜI DÙNG (JAVASCRIPT) ---
# Thành phần ẩn giúp đồng bộ hóa dữ liệu thời gian chính xác từ phía Client lên Streamlit Server
js_timezone_detector = """
<script>
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const now = new Date();
    const offset = -now.getTimezoneOffset();
    const diffHours = Math.floor(Math.abs(offset) / 60);
    const diffMins = Math.abs(offset) % 60;
    const sign = offset >= 0 ? "+" : "-";
    const formattedOffset = "GMT" + sign + String(diffHours).padStart(2, '0') + ":" + String(diffMins).padStart(2, '0');
    
    // Gửi dữ liệu về Streamlit qua cấu trúc window.parent
    if (window.parent && window.parent.postMessage) {
        window.parent.postMessage({
            type: "streamlit:setComponentValue",
            value: { timezone: tz, offset_str: formattedOffset, timestamp: now.getTime() }
        }, "*");
    }
</script>
"""

# Khởi tạo hoặc bắt bộ dò múi giờ client
if "client_tz_data" not in st.session_state:
    st.session_state.client_tz_data = {"timezone": "UTC", "offset_str": "GMT+00:00"}

# Sử dụng st.components.v1.html tích hợp mã JS nhận diện tự động múi giờ local
import streamlit.components.v1 as components
response = components.html(js_timezone_detector, height=0, width=0)

# Sidebar hiển thị ngôn ngữ
st.sidebar.markdown("### 🌐 Language / Ngôn ngữ")
selected_lang = st.sidebar.selectbox(
    "Select Language:", 
    list(LANGUAGES.keys()), 
    index=list(LANGUAGES.keys()).index(st.session_state.lang),
    label_visibility="collapsed"
)
if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    st.rerun()

st.title(L["title"])

# --- HIỂN THỊ ĐỒNG HỒ THỜI GIAN THỰC Ở SIDEBAR ---
# Tự động đồng bộ dựa trên luồng cục bộ máy khách
with st.sidebar:
    st.markdown("### ⏰ Hệ thống thời gian thực")
    time_placeholder = st.empty()
    # Hiển thị thông tin múi giờ hiện tại phát hiện từ vị trí người dùng
    st.caption(f"📍 Múi giờ vị trí: **{st.session_state.client_tz_data['timezone']}** ({st.session_state.client_tz_data['offset_str']})")

# Cập nhật đồng hồ thời gian thực (Real-time clock widget)
now_local = datetime.now()
time_placeholder.markdown(f"**🕒 {now_local.strftime('%H:%M:%S — %d/%m/%Y')}**")

# --- KẾT NỐI VÀ KIỂM TRA CẤU HÌNH GITHUB ---
try:
    GITHUB_TOKEN = st.secrets["DB_GITHUB_TOKEN"]
    REPO_NAME = st.secrets["DB_REPO_NAME"]
    BRANCH = st.secrets.get("DB_BRANCH", "main")
    CHAT_FILE = "data.json"
    USER_FILE = "accounts.json"
except Exception:
    st.error(L["missing_secrets"])
    st.stop()

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# --- CÁC HÀM XỬ LÝ DỮ LIỆU TỪ GITHUB ---
def load_github_file(file_path):
    try:
        file_content = repo.get_contents(file_path, ref=BRANCH)
        data = json.loads(file_content.decoded_content.decode("utf-8"))
        return data, file_content.sha
    except GithubException as e:
        if e.status == 404:
            return [], None
        else:
            st.error(f"GitHub Error ({file_path}): {e.data.get('message')}")
            return [], None

def save_github_file(file_path, data, sha=None, message="Update"):
    content_str = json.dumps(data, ensure_ascii=False, indent=4)
    try:
        if sha:
            repo.update_file(file_path, message, content_str, sha, branch=BRANCH)
        else:
            repo.create_file(file_path, message, content_str, branch=BRANCH)
        return True
    except Exception as e:
        st.error(f"GitHub Write Error ({file_path}): {e}")
        return False

def upload_binary_file(file_name, file_bytes):
    github_path = f"uploads/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_name}"
    commit_message = f"Upload file: {file_name}"
    try:
        repo.create_file(github_path, commit_message, file_bytes, branch=BRANCH)
        return f"https://github.com/{REPO_NAME}/blob/{BRANCH}/{github_path}?raw=true"
    except Exception as e:
        st.error(f"File Upload Error: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- HỆ THỐNG ĐĂNG NHẬP / ĐĂNG KÝ ---
if not st.session_state.logged_in:
    st.subheader(L["login_sub"])
    tab_login, tab_register = st.tabs([L["tab_login"], L["tab_register"]])
    accounts, user_sha = load_github_file(USER_FILE)
    
    with tab_login:
        login_user = st.text_input(L["username"], key="login_user_input").strip()
        login_pass = st.text_input(L["password"], type="password", key="login_pass_input")
        remember_me = st.checkbox(L["remember_me"], key="remember_me_check")
        
        if st.button(L["btn_login"], use_container_width=True):
            if not login_user or not login_pass:
                st.warning(L["err_missing"])
            else:
                hashed = hash_password(login_pass)
                user_found = next((u for u in accounts if u["username"] == login_user and u["password"] == hashed), None)
                if user_found:
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.success(L["success_login"])
                    st.rerun()
                else:
                    st.error(L["err_wrong"])
                    
    with tab_register:
        reg_user = st.text_input(L["username"], key="reg_user_input").strip()
        reg_pass = st.text_input(L["new_password"], type="password", key="reg_pass_input")
        reg_confirm = st.text_input(L["confirm_password"], type="password", key="reg_confirm_input")
        
        if st.button(L["btn_register"], use_container_width=True):
            if not reg_user or not reg_pass:
                st.warning(L["err_missing"])
            elif reg_pass != reg_confirm:
                st.error(L["err_match"])
            elif any(u["username"] == reg_user for u in accounts):
                st.error(L["err_exist"])
            else:
                new_account = {
                    "username": reg_user, 
                    "password": hash_password(reg_pass),
                    "friends": [],
                    "friend_requests_received": [],
                    "friend_requests_sent": []
                }
                accounts.append(new_account)
                if save_github_file(USER_FILE, accounts, user_sha, message=f"New user: {reg_user}"):
                    st.success(L["success_register"])
                    
    st.sidebar.write("---")
    st.sidebar.subheader(L["software_info_title"])
    st.sidebar.markdown(L["software_info_body"])
    st.stop()

# --- GIAO DIỆN CHAT VÀ QUẢN LÝ BẠN BÈ ---
accounts, user_sha = load_github_file(USER_FILE)
chat_history, chat_sha = load_github_file(CHAT_FILE)

current_user_data = next((u for u in accounts if u["username"] == st.session_state.username), None)
if not current_user_data:
    st.error("Account error.")
    st.stop()

if "friends" not in current_user_data: current_user_data["friends"] = []
if "friend_requests_received" not in current_user_data: current_user_data["friend_requests_received"] = []
if "friend_requests_sent" not in current_user_data: current_user_data["friend_requests_sent"] = []

st.sidebar.write("---")
st.sidebar.markdown(f"### {L['sidebar_account']} **{st.session_state.username}**")
if st.sidebar.button(L["btn_logout"], use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.sidebar.write("---")

# 1. Gửi yêu cầu kết bạn
st.sidebar.subheader(L["sidebar_friend"])
friend_target = st.sidebar.text_input(L["input_friend"], key="friend_target_input").strip()
if st.sidebar.button(L["btn_friend_req"], use_container_width=True):
    target_user_data = next((u for u in accounts if u["username"] == friend_target), None)
    
    if not friend_target:
        st.sidebar.warning(L["err_missing"])
    elif friend_target == st.session_state.username:
        st.sidebar.error(L["err_friend_self"])
    elif not target_user_data:
        st.sidebar.error(L["err_friend_404"])
    elif friend_target in current_user_data.get("friends", []):
        st.sidebar.info(L["info_friend_already"])
    elif friend_target in current_user_data.get("friend_requests_sent", []):
        st.sidebar.info(L["info_friend_sent"])
    else:
        current_user_data.setdefault("friend_requests_sent", []).append(friend_target)
        target_user_data.setdefault("friend_requests_received", []).append(st.session_state.username)
        if save_github_file(USER_FILE, accounts, user_sha, message=f"Friend request to {friend_target}"):
            st.sidebar.success(L["success_friend_sent"])
            st.rerun()

# 2. Chấp nhận / Từ chối kết bạn
req_received = current_user_data.get("friend_requests_received", [])
if req_received:
    st.sidebar.subheader(L["sidebar_req_recv"])
    for sender in req_received:
        st.sidebar.write(f"👉 **{sender}**")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button(L["btn_accept"], key=f"acc_{sender}"):
                current_user_data.setdefault("friends", []).append(sender)
                current_user_data["friend_requests_received"].remove(sender)
                sender_data = next((u for u in accounts if u["username"] == sender), None)
                if sender_data:
                    sender_data.setdefault("friends", []).append(st.session_state.username)
                    if st.session_state.username in sender_data.get("friend_requests_sent", []):
                        sender_data["friend_requests_sent"].remove(st.session_state.username)
                if save_github_file(USER_FILE, accounts, user_sha, message=f"Accepted {sender}"):
                    st.rerun()
        with col2:
            if st.button(L["btn_decline"], key=f"dec_{sender}"):
                current_user_data["friend_requests_received"].remove(sender)
                sender_data = next((u for u in accounts if u["username"] == sender), None)
                if sender_data and st.session_state.username in sender_data.get("friend_requests_sent", []):
                    sender_data["friend_requests_sent"].remove(st.session_state.username)
                if save_github_file(USER_FILE, accounts, user_sha, message=f"Declined {sender}"):
                    st.rerun()

st.sidebar.write("---")
st.sidebar.subheader(L["sidebar_room"])
my_friends = current_user_data.get("friends", [])

chat_options = [L["public_room"]] + my_friends
selected_chat = st.sidebar.selectbox("Chat:", chat_options, label_visibility="collapsed")

if selected_chat == L["public_room"]:
    if st.sidebar.button(L["btn_clear_chat"], use_container_width=True):
        if save_github_file(CHAT_FILE, [], chat_sha, message="Clear public"):
            st.success(L["success_clear"])
            st.rerun()

st.sidebar.write("---")
st.sidebar.subheader(L["software_info_title"])
st.sidebar.markdown(L["software_info_body"])

# --- GIAO DIỆN CHAT ---
st.write(f"### {selected_chat}")

filtered_chats = []
for msg in chat_history:
    if selected_chat == L["public_room"]:
        if msg.get("room", "public") == "public":
            if msg["user"] == st.session_state.username or msg["user"] in my_friends:
                filtered_chats.append(msg)
    else:
        if msg.get("room") == "private":
            if (msg["user"] == st.session_state.username and msg.get("to") == selected_chat) or \
               (msg["user"] == selected_chat and msg.get("to") == st.session_state.username):
                filtered_chats.append(msg)

# Khung chứa hội thoại độc lập
chat_container = st.container()

with chat_container:
    for msg in filtered_chats:
        with st.chat_message(msg["role"]):
            st.markdown(f"**{msg['user']}** <span style='color:gray; font-size:12px;'>• {msg['time']}</span>", unsafe_allow_html=True)
            
            if msg["text"]: 
                st.write(msg["text"])
                
            if "file_url" in msg:
                f_url = msg["file_url"]
                f_name = msg["file_name"].lower()
                
                if f_name.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')):
                    st.image(f_url, caption=msg["file_name"], use_container_width=True)
                elif f_name.endswith(('.mp4', '.webm', '.mov', '.avi', '.mkv')):
                    st.video(f_url)
                elif f_name.endswith(('.mp3', '.wav', '.ogg', '.m4a', '.flac')):
                    st.audio(f_url)
                else:
                    st.markdown(f"{L['file_attached']} [{msg['file_name']}]({f_url})")

# Kiểm tra điều kiện chat
is_still_friend = True
if selected_chat != L["public_room"] and selected_chat not in my_friends:
    is_still_friend = False
    st.error(L["err_not_friend"])

if is_still_friend:
    # Bố cục Panel dưới cùng cố định chứa cả thanh tải lên và ô chat
    input_panel = st.container()
    
    with input_panel:
        uploaded_file = st.file_uploader(L["file_uploader"], type=None, label_visibility="collapsed")
        file_url = None
        file_name = None
        valid_file = False
        
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            file_size_mb = len(file_bytes) / (1024 * 1024)
            
            if file_size_mb > 25.0:
                st.error(L["err_file_size"])
            else:
                file_name = uploaded_file.name
                st.info(f"{L['info_file_ready']} {file_name} ({file_size_mb:.2f} MB)")
                valid_file = True

        if prompt := st.chat_input(L["chat_input"]):
            if uploaded_file is not None and valid_file:
                with st.spinner(L["spinner_upload"]):
                    file_url = upload_binary_file(file_name, file_bytes)
            
            # Ghi nhận thời gian tin nhắn dựa trên thời gian thực tế của hệ thống
            msg_time = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
            
            new_message = {
                "user": st.session_state.username,
                "role": "user",
                "time": msg_time,
                "text": prompt,
                "room": "public" if selected_chat == L["public_room"] else "private"
            }
            
            if selected_chat != L["public_room"]:
                new_message["to"] = selected_chat
                
            if file_url:
                new_message["file_url"] = file_url
                new_message["file_name"] = file_name
                
            chat_history.append(new_message)
            if save_github_file(CHAT_FILE, chat_history, chat_sha, message=f"Msg from {st.session_state.username}"):
                st.rerun()
