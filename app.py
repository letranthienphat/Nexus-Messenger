"""
LTTP Messenger v3.1 - Fast UI + Guest Mode
==========================================
Features: Guest mode (name-only), real-time fragment, glassmorphism UI,
          emoji injection, reply, search, online status, retry-safe writes.
"""

import streamlit as st
import json
import hashlib
import time
import re
from github import Github, GithubException
from datetime import datetime
import zoneinfo

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
APP_NAME = "LTTP Messenger"
APP_VERSION = "3.1.0 (Fast UI · Guest)"
MAX_FILE_MB = 25
MAX_CHAT_ENTRIES = 800
SESSION_TIMEOUT_MIN = 60
REFRESH_INTERVAL = "4s"
GUEST_PREFIX = "guest_"           # prefix phân biệt guest với user thật
GUEST_ROOM = "__guest_lobby__"    # phòng riêng cho guest (không lẫn public)
ONLINE_WINDOW_SEC = 300
LAST_SEEN_SAVE_INTERVAL = 120     # giây — throttle update last_seen

# ═══════════════════════════════════════════════════════════════
#  SESSION STATE INIT — PHẢI CHẠY TRƯỚC KHI TÍNH L
# ═══════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "lang": "Tiếng Việt",
        "logged_in": False,
        "is_guest": False,
        "username": "",
        "client_timezone": "Asia/Ho_Chi_Minh",
        "last_activity": time.time(),
        "last_seen_saved": 0,
        "reply_to": None,
        "search_query": "",
        "pending_emoji": "",
        "chat_buffer": "",
        "prev_room": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

init_state()

# ═══════════════════════════════════════════════════════════════
#  i18n
# ═══════════════════════════════════════════════════════════════
LANGUAGES = {
    "Tiếng Việt": {
        "app_tagline": "Trò chuyện nhanh, bảo mật, không giới hạn.",
        "login": "Đăng nhập", "register": "Đăng ký", "guest": "Khách",
        "logout": "Đăng xuất",
        "username": "Tên đăng nhập", "password": "Mật khẩu",
        "new_password": "Mật khẩu mới", "confirm_password": "Xác nhận mật khẩu",
        "btn_login": "🔓 Đăng nhập", "btn_register": "✨ Tạo tài khoản",
        "btn_guest": "🎭 Vào với tư cách khách",
        "guest_name": "Tên hiển thị của bạn",
        "guest_note": "Chế độ khách: chỉ chat ở sảnh khách, không kết bạn, không lưu tin nhắn riêng.",
        "guest_room": "🎭 Sảnh khách",
        "err_guest_name": "Tên khách phải từ 2-20 ký tự, không chứa ký tự đặc biệt.",
        "err_missing": "Vui lòng nhập đầy đủ thông tin.",
        "err_wrong": "Sai tên đăng nhập hoặc mật khẩu.",
        "err_match": "Mật khẩu xác nhận không khớp.",
        "err_exist": "Tên đăng nhập đã tồn tại.",
        "err_username_invalid": "Tên đăng nhập chỉ chứa chữ, số, dấu _ (3-24 ký tự).",
        "err_password_short": "Mật khẩu phải từ 6 ký tự.",
        "success_register": "Đăng ký thành công! Hãy đăng nhập.",
        "sidebar_rooms": "Phòng chat",
        "public_room": "🌐 Hộp thư chung",
        "friends": "Bạn bè",
        "add_friend": "Kết bạn",
        "friend_username": "Tên người dùng",
        "btn_send_req": "Gửi lời mời",
        "pending_requests": "Lời mời đang chờ",
        "btn_accept": "Chấp nhận", "btn_decline": "Từ chối",
        "err_friend_self": "Không thể kết bạn với chính mình.",
        "err_friend_404": "Không tìm thấy người dùng.",
        "info_friend_already": "Đã là bạn bè.",
        "info_friend_sent": "Đã gửi lời mời trước đó.",
        "success_friend_sent": "Đã gửi lời mời kết bạn!",
        "chat_placeholder": "Nhập tin nhắn...",
        "attach": "Đính kèm",
        "send_file": "Gửi tệp",
        "err_file_size": f"Tệp vượt quá {MAX_FILE_MB}MB.",
        "uploading": "Đang tải lên...",
        "err_not_friend": "Bạn không thể nhắn tin với người này.",
        "clear_chat": "Xóa lịch sử",
        "success_clear": "Đã xóa lịch sử.",
        "no_messages": "Chưa có tin nhắn nào. Hãy bắt đầu cuộc trò chuyện!",
        "online": "Đang hoạt động",
        "search": "Tìm kiếm tin nhắn...",
        "info": "Thông tin",
        "reply": "Trả lời",
        "cancel_reply": "Hủy",
        "session_expired": "Phiên đăng nhập đã hết hạn.",
        "missing_secrets": "Thiếu cấu hình Secrets (DB_GITHUB_TOKEN, DB_REPO_NAME).",
        "emoji": "Cảm xúc",
        "online_users": "online",
        "guest_badge": "🎭 Khách",
        "guest_leave": "🚪 Rời sảnh khách",
        "guest_welcome": "Chào mừng khách",
        "search_clear": "Xóa tìm kiếm",
    },
    "English": {
        "app_tagline": "Fast, secure, unlimited chat.",
        "login": "Login", "register": "Register", "guest": "Guest",
        "logout": "Logout",
        "username": "Username", "password": "Password",
        "new_password": "New password", "confirm_password": "Confirm password",
        "btn_login": "🔓 Sign in", "btn_register": "✨ Create account",
        "btn_guest": "🎭 Continue as guest",
        "guest_name": "Your display name",
        "guest_note": "Guest mode: chat in guest lobby only, no friends, no private messages.",
        "guest_room": "🎭 Guest Lobby",
        "err_guest_name": "Guest name: 2-20 chars, no special characters.",
        "err_missing": "Please fill in all fields.",
        "err_wrong": "Incorrect username or password.",
        "err_match": "Passwords do not match.",
        "err_exist": "Username already exists.",
        "err_username_invalid": "Username: letters, digits, _ (3-24 chars).",
        "err_password_short": "Password must be at least 6 characters.",
        "success_register": "Registered! Please sign in.",
        "sidebar_rooms": "Chat rooms",
        "public_room": "🌐 Public Box",
        "friends": "Friends",
        "add_friend": "Add friend",
        "friend_username": "Username",
        "btn_send_req": "Send request",
        "pending_requests": "Pending requests",
        "btn_accept": "Accept", "btn_decline": "Decline",
        "err_friend_self": "Cannot add yourself.",
        "err_friend_404": "User not found.",
        "info_friend_already": "Already friends.",
        "info_friend_sent": "Request already sent.",
        "success_friend_sent": "Friend request sent!",
        "chat_placeholder": "Type a message...",
        "attach": "Attach",
        "send_file": "Send file",
        "err_file_size": f"File exceeds {MAX_FILE_MB}MB.",
        "uploading": "Uploading...",
        "err_not_friend": "You cannot chat with this user.",
        "clear_chat": "Clear history",
        "success_clear": "History cleared.",
        "no_messages": "No messages yet. Start the conversation!",
        "online": "Online",
        "search": "Search messages...",
        "info": "Info",
        "reply": "Reply",
        "cancel_reply": "Cancel",
        "session_expired": "Session expired.",
        "missing_secrets": "Missing secrets (DB_GITHUB_TOKEN, DB_REPO_NAME).",
        "emoji": "Emoji",
        "online_users": "online",
        "guest_badge": "🎭 Guest",
        "guest_leave": "🚪 Leave guest lobby",
        "guest_welcome": "Welcome, guest",
        "search_clear": "Clear search",
    },
}
L = LANGUAGES[st.session_state.lang]

# ═══════════════════════════════════════════════════════════════
#  PAGE CONFIG & CSS
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title=APP_NAME, page_icon="💬", layout="wide",
    initial_sidebar_state="expanded"
)

FAST_UI_CSS = """
<style>
:root{
  --bg:#0b1020; --card:rgba(255,255,255,.06);
  --border:rgba(255,255,255,.12); --text:#e9ecf5; --muted:#9aa3bd;
  --accent:#7c5cff; --accent2:#22d3ee; --success:#22c55e; --danger:#ef4444;
  --warn:#f59e0b;
  --bubble-me:linear-gradient(135deg,#7c5cff,#4f46e5);
  --bubble-other:rgba(255,255,255,.08);
}
.stApp{
  background:radial-gradient(1200px 700px at 10% -10%,#1b1f3b 0%,transparent 55%),
             radial-gradient(1000px 600px at 110% 10%,#0f3d4a 0%,transparent 50%),
             var(--bg);
  color:var(--text);
}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:1rem;padding-bottom:3rem;max-width:1150px;}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:8px}
.stTextInput input,.stTextArea textarea{
  background:var(--card)!important;border:1px solid var(--border)!important;
  color:var(--text)!important;border-radius:12px!important;padding:10px 12px!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 2px rgba(124,92,255,.25)!important;
}
.stButton>button{
  background:var(--card);border:1px solid var(--border);color:var(--text);
  border-radius:12px;font-weight:600;transition:all .18s ease;
}
.stButton>button:hover{
  transform:translateY(-1px);border-color:var(--accent);
  box-shadow:0 6px 20px rgba(124,92,255,.25);
}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  border:none;color:#fff;
}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:transparent}
.stTabs [data-baseweb="tab"]{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:8px 16px;color:var(--muted);
}
.stTabs [aria-selected="true"]{
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:#fff!important;border-color:transparent!important;
}
[data-testid="stChatMessage"]{
  background:var(--bubble-other);border:1px solid var(--border);
  border-radius:16px;padding:10px 14px;margin-bottom:8px;
  backdrop-filter:blur(8px);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]){
  background:var(--bubble-me);border-color:transparent;
}
.reply-preview{
  border-left:3px solid var(--accent);padding:4px 10px;margin:4px 0 8px 0;
  background:rgba(124,92,255,.1);border-radius:6px;font-size:.85rem;color:var(--muted);
}
.glass{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:16px 20px;backdrop-filter:blur(12px);
}
.hero{text-align:center;padding:26px 16px 8px 16px;}
.hero h1{
  font-size:2.4rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,#fff,#a5b4fc 60%,#22d3ee);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  margin-bottom:6px;
}
.hero p{color:var(--muted);font-size:1rem}
.avatar{
  width:38px;height:38px;border-radius:50%;display:inline-flex;
  align-items:center;justify-content:center;font-weight:700;color:#fff;
  background:linear-gradient(135deg,#7c5cff,#22d3ee);
  flex:0 0 38px;font-size:.9rem;
}
.avatar-guest{background:linear-gradient(135deg,#f59e0b,#ef4444);}
.dot-online{
  display:inline-block;width:8px;height:8px;border-radius:50%;
  background:var(--success);margin-right:6px;box-shadow:0 0 8px var(--success);
}
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#0d1224,#0b1020);
  border-right:1px solid var(--border);
}
.room-header{
  display:flex;align-items:center;gap:12px;
  padding:12px 16px;border-radius:16px;
  background:var(--card);border:1px solid var(--border);margin-bottom:12px;
}
.room-header h3{margin:0;font-size:1.15rem}
.room-header small{color:var(--muted)}
.badge{
  background:var(--danger);color:#fff;border-radius:10px;
  padding:1px 7px;font-size:.7rem;font-weight:700;margin-left:6px;
}
.badge-guest{background:var(--warn);color:#000;}
.file-chip{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(124,92,255,.15);border:1px solid var(--accent);
  border-radius:10px;padding:6px 12px;margin:4px 0;font-size:.85rem;
}
[data-testid="stChatInput"] textarea{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:16px!important;color:var(--text)!important;
}
.guest-banner{
  background:linear-gradient(135deg,rgba(245,158,11,.15),rgba(239,68,68,.15));
  border:1px solid var(--warn);border-radius:12px;
  padding:8px 14px;margin-bottom:12px;font-size:.9rem;
}
</style>
"""
st.markdown(FAST_UI_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  TIMEZONE
# ═══════════════════════════════════════════════════════════════
def detect_timezone():
    try:
        from streamlit_js_eval import streamlit_js_eval
        tz = streamlit_js_eval(
            js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone",
            key="tz_eval"
        )
        if tz and isinstance(tz, str):
            st.session_state.client_timezone = tz
    except Exception:
        pass

detect_timezone()

def now_str(fmt="%H:%M %d/%m/%Y"):
    try:
        tz = zoneinfo.ZoneInfo(st.session_state.client_timezone)
        return datetime.now(tz).strftime(fmt)
    except Exception:
        return datetime.now().strftime(fmt)

# ═══════════════════════════════════════════════════════════════
#  GITHUB BACKEND
# ═══════════════════════════════════════════════════════════════
try:
    GITHUB_TOKEN = st.secrets["DB_GITHUB_TOKEN"]
    REPO_NAME = st.secrets["DB_REPO_NAME"]
    BRANCH = st.secrets.get("DB_BRANCH", "main")
except Exception:
    st.error(L["missing_secrets"])
    st.stop()

CHAT_FILE = "data.json"
USER_FILE = "accounts.json"

@st.cache_resource(show_spinner=False)
def get_repo():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)

repo = get_repo()

def load_github_file(path):
    try:
        fc = repo.get_contents(path, ref=BRANCH)
        return json.loads(fc.decoded_content.decode("utf-8")), fc.sha
    except GithubException as e:
        if e.status == 404:
            return [], None
        st.error(f"GitHub ({path}): {e.data.get('message')}")
        return [], None
    except Exception as e:
        st.error(f"Load error: {e}")
        return [], None

def save_github_file(path, data, sha=None, message="update", retries=4):
    """Return (success, new_sha) để caller cập nhật SHA tránh 409."""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    for attempt in range(retries):
        try:
            if sha:
                res = repo.update_file(path, message, content, sha, branch=BRANCH)
            else:
                res = repo.create_file(path, message, content, branch=BRANCH)
            return True, res["content"].sha
        except GithubException as e:
            if e.status in (409, 422) and attempt < retries - 1:
                time.sleep(0.4 * (attempt + 1))
                try:
                    sha = repo.get_contents(path, ref=BRANCH).sha
                except Exception:
                    sha = None
                continue
            st.error(f"Save error ({path}): {e}")
            return False, sha
        except Exception as e:
            st.error(f"Save error ({path}): {e}")
            return False, sha
    return False, sha

def upload_binary(fname, fbytes):
    path = f"uploads/{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{fname}"
    try:
        repo.create_file(path, f"Upload {fname}", fbytes, branch=BRANCH)
        return f"https://github.com/{REPO_NAME}/blob/{BRANCH}/{path}?raw=true"
    except Exception as e:
        st.error(f"Upload: {e}")
        return None

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def initials(name):
    clean = name.replace(GUEST_PREFIX, "")
    return (clean[:2] if clean else "??").upper()

def activity_tick():
    st.session_state.last_activity = time.time()

def check_session():
    if st.session_state.logged_in and not st.session_state.is_guest:
        idle = time.time() - st.session_state.last_activity
        if idle > SESSION_TIMEOUT_MIN * 60:
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.warning(L["session_expired"])
            st.rerun()

def validate_username(u):
    return bool(re.match(r"^[A-Za-z0-9_]{3,24}$", u))

def validate_guest_name(n):
    return bool(re.match(r"^[A-Za-zÀ-ỹ0-9 _]{2,20}$", n))

def is_online(user):
    try:
        return (time.time() - float(user.get("last_seen", 0))) < ONLINE_WINDOW_SEC
    except Exception:
        return False

def save_last_seen(accounts, acc_sha):
    """Throttle update last_seen để tránh spam GitHub API."""
    now = time.time()
    if now - st.session_state.last_seen_saved < LAST_SEEN_SAVE_INTERVAL:
        return acc_sha
    me = next((x for x in accounts if x["username"] == st.session_state.username), None)
    if me:
        me["last_seen"] = now
        ok, new_sha = save_github_file(USER_FILE, accounts, acc_sha, "heartbeat")
        if ok:
            st.session_state.last_seen_saved = now
            return new_sha
    return acc_sha

def logout():
    st.session_state.logged_in = False
    st.session_state.is_guest = False
    st.session_state.username = ""
    st.session_state.reply_to = None
    st.session_state.search_query = ""
    st.session_state.chat_buffer = ""
    st.session_state.prev_room = None

# ═══════════════════════════════════════════════════════════════
#  SIDEBAR TOP (Language + Clock) — luôn hiển thị
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"### 💬 **{APP_NAME}**")
    st.caption(f"v{APP_VERSION}")
    col_lang, col_clock = st.columns([1, 1])
    with col_lang:
        sel = st.selectbox(
            "🌐", list(LANGUAGES.keys()),
            index=list(LANGUAGES.keys()).index(st.session_state.lang),
            label_visibility="collapsed"
        )
        if sel != st.session_state.lang:
            st.session_state.lang = sel
            st.rerun()
    with col_clock:
        st.markdown(
            f"<div style='text-align:right;font-weight:600;'>"
            f"🕒 {now_str('%H:%M')}<br>"
            f"<small style='color:var(--muted);font-weight:400;'>{now_str('%d/%m/%Y')}</small>"
            f"</div>", unsafe_allow_html=True
        )
    st.divider()

# ═══════════════════════════════════════════════════════════════
#  AUTH SCREEN (LOGIN / REGISTER / GUEST)
# ═══════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.markdown(f"""
    <div class="hero">
      <h1>{APP_NAME}</h1>
      <p>{L['app_tagline']}</p>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        tab_login, tab_reg, tab_guest = st.tabs([
            f"🔑 {L['login']}",
            f"📝 {L['register']}",
            f"🎭 {L['guest']}",
        ])
        accounts, acc_sha = load_github_file(USER_FILE)

        # ---- LOGIN ----
        with tab_login:
            u = st.text_input(L["username"], key="li_u")
            p = st.text_input(L["password"], type="password", key="li_p")
            if st.button(L["btn_login"], use_container_width=True, type="primary", key="li_btn"):
                if not u or not p:
                    st.warning(L["err_missing"])
                else:
                    h = hash_password(p)
                    found = next((x for x in accounts if x["username"] == u and x["password"] == h), None)
                    if found:
                        st.session_state.logged_in = True
                        st.session_state.is_guest = False
                        st.session_state.username = u
                        st.session_state.last_seen_saved = 0
                        activity_tick()
                        st.rerun()
                    else:
                        st.error(L["err_wrong"])

        # ---- REGISTER ----
        with tab_reg:
            ru = st.text_input(L["username"], key="rg_u")
            rp = st.text_input(L["new_password"], type="password", key="rg_p")
            rc = st.text_input(L["confirm_password"], type="password", key="rg_c")
            if st.button(L["btn_register"], use_container_width=True, type="primary", key="rg_btn"):
                if not ru or not rp or not rc:
                    st.warning(L["err_missing"])
                elif not validate_username(ru):
                    st.error(L["err_username_invalid"])
                elif len(rp) < 6:
                    st.error(L["err_password_short"])
                elif rp != rc:
                    st.error(L["err_match"])
                elif any(x["username"].lower() == ru.lower() for x in accounts):
                    st.error(L["err_exist"])
                else:
                    accounts.append({
                        "username": ru,
                        "password": hash_password(rp),
                        "friends": [],
                        "friend_requests_received": [],
                        "friend_requests_sent": [],
                        "last_seen": time.time(),
                    })
                    ok, _ = save_github_file(USER_FILE, accounts, acc_sha, f"new user {ru}")
                    if ok:
                        st.success(L["success_register"])

        # ---- GUEST ----
        with tab_guest:
            st.info(L["guest_note"])
            gname = st.text_input(L["guest_name"], key="guest_n")
            if st.button(L["btn_guest"], use_container_width=True, type="primary", key="guest_btn"):
                if not gname or not validate_guest_name(gname):
                    st.error(L["err_guest_name"])
                else:
                    # Tên nội bộ: guest_<name> để tránh trùng user thật
                    internal = f"{GUEST_PREFIX}{gname}_{int(time.time()) % 100000}"
                    st.session_state.logged_in = True
                    st.session_state.is_guest = True
                    st.session_state.username = internal
                    st.session_state.guest_display = gname
                    activity_tick()
                    st.rerun()
    st.stop()

# ═══════════════════════════════════════════════════════════════
#  LOGGED IN (user hoặc guest)
# ═══════════════════════════════════════════════════════════════
check_session()
activity_tick()

is_guest = st.session_state.is_guest
display_name = st.session_state.get("guest_display", st.session_state.username) if is_guest else st.session_state.username

accounts, acc_sha = load_github_file(USER_FILE)
chat_all, chat_sha = load_github_file(CHAT_FILE)

# Với guest: KHÔNG load/sửa accounts, không check friend
if not is_guest:
    me = next((x for x in accounts if x["username"] == st.session_state.username), None)
    if not me:
        st.error("Account not found.")
        logout()
        st.rerun()
    for k in ("friends", "friend_requests_received", "friend_requests_sent"):
        me.setdefault(k, [])
    acc_sha = save_last_seen(accounts, acc_sha)
    my_friends = me.get("friends", [])
    online_friends = [
        f for f in my_friends
        if (lambda u: u and is_online(u))(
            next((x for x in accounts if x["username"] == f), None)
        )
    ]
else:
    my_friends = []
    online_friends = []
    me = None

# ═══════════════════════════════════════════════════════════════
#  SIDEBAR (user/guest)
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    avatar_cls = "avatar avatar-guest" if is_guest else "avatar"
    badge_html = f"<span class='badge badge-guest'>{L['guest_badge']}</span>" if is_guest else ""
    sub_line = (
        f"<span style='color:var(--muted);'>{L['guest_note'][:40]}…</span>"
        if is_guest
        else f"<span class='dot-online'></span>{len(online_friends)} {L['online_users']}"
    )
    st.markdown(f"""
    <div class="glass" style="display:flex;gap:12px;align-items:center;">
      <div class="{avatar_cls}">{initials(display_name)}</div>
      <div style="flex:1;min-width:0;">
        <div style="font-weight:700;">{display_name} {badge_html}</div>
        <div style="font-size:.78rem;">{sub_line}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(L["logout"] if not is_guest else L["guest_leave"], use_container_width=True):
        logout()
        st.rerun()
    st.divider()

    # --- ROOMS ---
    st.markdown(f"#### {L['sidebar_rooms']}")
    if is_guest:
        room_labels = [L["guest_room"]]
        room_keys = [GUEST_ROOM]
    else:
        room_labels = [L["public_room"]] + [f"💬 {f}" for f in my_friends]
        room_keys = ["__public__"] + my_friends

    # Đảm bảo index hợp lệ khi list thay đổi
    current_room = st.session_state.get("room_select", 0)
    if not isinstance(current_room, int) or current_room >= len(room_keys):
        st.session_state.room_select = 0
        current_room = 0

    selected_idx = st.radio(
        "room", range(len(room_keys)),
        format_func=lambda i: room_labels[i],
        label_visibility="collapsed",
        key="room_select"
    )
    selected_key = room_keys[selected_idx]

    # Reset state khi đổi phòng
    if st.session_state.prev_room != selected_key:
        st.session_state.prev_room = selected_key
        st.session_state.search_query = ""
        st.session_state.reply_to = None

    st.divider()

    # --- FRIEND SECTION (chỉ user thật) ---
    if not is_guest:
        with st.expander(f"➕ {L['add_friend']}", expanded=False):
            target = st.text_input(L["friend_username"], key="ft_input").strip()
            if st.button(L["btn_send_req"], use_container_width=True, key="add_btn"):
                tu = next((x for x in accounts if x["username"] == target), None)
                if not target:
                    st.warning(L["err_missing"])
                elif target == st.session_state.username:
                    st.error(L["err_friend_self"])
                elif not tu:
                    st.error(L["err_friend_404"])
                elif target in my_friends:
                    st.info(L["info_friend_already"])
                elif target in me["friend_requests_sent"]:
                    st.info(L["info_friend_sent"])
                else:
                    me["friend_requests_sent"].append(target)
                    tu["friend_requests_received"].append(st.session_state.username)
                    ok, _ = save_github_file(USER_FILE, accounts, acc_sha, f"req {target}")
                    if ok:
                        st.success(L["success_friend_sent"])
                        st.rerun()

        if me["friend_requests_received"]:
            st.markdown(f"#### 📥 {L['pending_requests']}")
            for sender in list(me["friend_requests_received"]):
                with st.container(border=True):
                    st.markdown(
                        f"<div class='avatar' style='width:26px;height:26px;font-size:.7rem;'>"
                        f"{initials(sender)}</div> **{sender}**",
                        unsafe_allow_html=True
                    )
                    c1, c2 = st.columns(2)
                    if c1.button("✅", key=f"a_{sender}", use_container_width=True):
                        me["friends"].append(sender)
                        me["friend_requests_received"].remove(sender)
                        sd = next((x for x in accounts if x["username"] == sender), None)
                        if sd:
                            sd.setdefault("friends", []).append(st.session_state.username)
                            if st.session_state.username in sd.get("friend_requests_sent", []):
                                sd["friend_requests_sent"].remove(st.session_state.username)
                        ok, _ = save_github_file(USER_FILE, accounts, acc_sha, "accept")
                        if ok:
                            st.rerun()
                    if c2.button("❌", key=f"d_{sender}", use_container_width=True):
                        me["friend_requests_received"].remove(sender)
                        ok, _ = save_github_file(USER_FILE, accounts, acc_sha, "decline")
                        if ok:
                            st.rerun()
            st.divider()

    st.caption(f"ℹ️ {APP_NAME} · v{APP_VERSION}")

# ═══════════════════════════════════════════════════════════════
#  MAIN CHAT AREA
# ═══════════════════════════════════════════════════════════════
is_public = selected_key == "__public__"
is_guest_room = selected_key == GUEST_ROOM

if is_guest_room:
    room_title = L["guest_room"]
elif is_public:
    room_title = L["public_room"]
else:
    room_title = f"💬 {selected_key}"

# --- ROOM HEADER ---
if is_guest_room:
    sub = f"🎭 {L['guest_note'][:60]}"
    avatar_char = "🎭"
elif is_public:
    sub = f"{len(my_friends)} {L['friends'].lower()} · {len(online_friends)} {L['online']}"
    avatar_char = "🌐"
else:
    sub = f"<span class='dot-online'></span>{L['online']}" if selected_key in online_friends else "offline"
    avatar_char = initials(selected_key)

st.markdown(f"""
<div class="room-header">
  <div class="avatar">{avatar_char}</div>
  <div style="flex:1;">
    <h3>{room_title}</h3>
    <small>{sub}</small>
  </div>
</div>
""", unsafe_allow_html=True)

if is_guest:
    st.markdown(f"<div class='guest-banner'>🎭 {L['guest_note']}</div>",
                unsafe_allow_html=True)

# --- MESSAGE FILTER FUNCTION ---
def get_room_messages(all_msgs, room_key):
    if room_key == GUEST_ROOM:
        return [m for m in all_msgs if m.get("room") == "guest"]
    if room_key == "__public__":
        return [
            m for m in all_msgs
            if m.get("room", "public") == "public"
            and (m["user"] == st.session_state.username or m["user"] in my_friends)
        ]
    return [
        m for m in all_msgs
        if m.get("room") == "private"
        and ((m["user"] == st.session_state.username and m.get("to") == room_key)
             or (m["user"] == room_key and m.get("to") == st.session_state.username))
    ]

# --- SEARCH ---
search_col, clear_col = st.columns([9, 1])
with search_col:
    search = st.text_input(
        "🔍 " + L["search"],
        value=st.session_state.search_query,
        key="search_input"
    )
    st.session_state.search_query = search
with clear_col:
    st.write("")
    if st.button("✖", help=L["search_clear"], use_container_width=True):
        st.session_state.search_query = ""
        st.rerun()

# --- MESSAGE RENDER (fragment) ---
def render_one_message(m):
    is_me = m["user"] == st.session_state.username
    avatar = "🧑" if is_me else ("🎭" if is_guest_room and m["user"].startswith(GUEST_PREFIX) else "👤")
    display_user = (
        m.get("display_name", m["user"])
        if m["user"].startswith(GUEST_PREFIX)
        else m["user"]
    )
    with st.chat_message(m["role"], avatar=avatar):
        if m.get("reply_to"):
            rp = m["reply_to"]
            st.markdown(
                f"<div class='reply-preview'>↪ <b>{rp.get('user','')}</b>: {rp.get('text','')[:80]}</div>",
                unsafe_allow_html=True
            )
        st.markdown(
            f"**{display_user}** "
            f"<span style='color:var(--muted);font-size:.75rem;'>· {m['time']}</span>",
            unsafe_allow_html=True
        )
        if m.get("text"):
            st.write(m["text"])
        if m.get("file_url"):
            fn = m["file_name"].lower()
            if fn.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
                st.image(m["file_url"], caption=m["file_name"], use_container_width=True)
            elif fn.endswith((".mp4", ".webm", ".mov", ".avi", ".mkv")):
                st.video(m["file_url"])
            elif fn.endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac")):
                st.audio(m["file_url"])
            else:
                st.markdown(f"📂 [{m['file_name']}]({m['file_url']})")
        if not is_me:
            if st.button("↩ " + L["reply"], key=f"rp_{id(m)}_{m.get('time','')}"):
                st.session_state.reply_to = {
                    "user": display_user, "text": m.get("text", "")[:120]
                }
                st.rerun()

@st.fragment(run_every=REFRESH_INTERVAL)
def live_messages_fragment(room_key, search_q):
    try:
        fresh, _ = load_github_file(CHAT_FILE)
    except Exception:
        fresh = chat_all
    msgs = get_room_messages(fresh, room_key)
    if search_q:
        q = search_q.lower()
        msgs = [m for m in msgs if q in (m.get("text", "") + m.get("user", "")).lower()]
    if not msgs:
        st.info(L["no_messages"])
        return
    for m in msgs:
        render_one_message(m)

live_messages_fragment(selected_key, st.session_state.search_query)

# ═══════════════════════════════════════════════════════════════
#  REPLY PREVIEW
# ═══════════════════════════════════════════════════════════════
if st.session_state.reply_to:
    rp = st.session_state.reply_to
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown(
            f"<div class='reply-preview'>↪ <b>{rp['user']}</b>: {rp['text']}</div>",
            unsafe_allow_html=True
        )
    with c2:
        if st.button("✖ " + L["cancel_reply"], use_container_width=True, key="cancel_reply_btn"):
            st.session_state.reply_to = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════
#  EMOJI INJECTION — thay thế chat_input bằng cách buffer
# ═══════════════════════════════════════════════════════════════
# Emoji popover đặt phía trên chat_input
emoji_col, attach_col = st.columns([1, 1])
with emoji_col:
    with st.popover("😀 " + L["emoji"], use_container_width=True):
        emojis = "😀 😂 😍 😎 🤔 😢 😡 👍 👎 ❤️ 🔥 🎉 ✅ ❌ 🚀 💯 👏 🙏 😴 🤝 🎯 ⚡ 💡 🌟 🍀"
        cols = st.columns(6)
        for i, e in enumerate(emojis.split()):
            if cols[i % 6].button(e, key=f"em_{i}", use_container_width=True):
                st.session_state.chat_buffer += e
                st.rerun()

with attach_col:
    with st.popover("📎 " + L["attach"], use_container_width=True):
        # Uploader NGOÀI popover không được — dùng st.file_uploader ở đây
        # Lưu ý: nếu đóng popover file mất, nên ta dùng session_state lưu bytes
        up = st.file_uploader(L["attach"], label_visibility="collapsed", key="fup")
        if up is not None:
            fb = up.read()
            mb = len(fb) / (1024 * 1024)
            if mb > MAX_FILE_MB:
                st.error(L["err_file_size"])
            else:
                st.markdown(f"<div class='file-chip'>📄 {up.name} · {mb:.2f} MB</div>",
                            unsafe_allow_html=True)
                if st.button(L["send_file"], use_container_width=True, key="send_file_btn"):
                    with st.spinner(L["uploading"]):
                        url = upload_binary(up.name, fb)
                    if url:
                        msg = {
                            "user": st.session_state.username,
                            "display_name": display_name,
                            "role": "user", "time": now_str(),
                            "text": "", "file_url": url, "file_name": up.name,
                            "room": "guest" if is_guest_room
                                    else ("public" if is_public else "private"),
                        }
                        if not is_public and not is_guest_room:
                            msg["to"] = selected_key
                        chat_all.append(msg)
                        if len(chat_all) > MAX_CHAT_ENTRIES:
                            chat_all[:] = chat_all[-MAX_CHAT_ENTRIES:]
                        ok, _ = save_github_file(CHAT_FILE, chat_all, chat_sha, "file")
                        if ok:
                            st.rerun()

# Chat input — inject buffer nếu có
if st.session_state.chat_buffer:
    st.caption(f"📝 Buffer: {st.session_state.chat_buffer}")

prompt = st.chat_input(L["chat_placeholder"])
if prompt is not None and prompt != "":
    final_text = (st.session_state.chat_buffer + prompt).strip()
    st.session_state.chat_buffer = ""
    if final_text:
        msg = {
            "user": st.session_state.username,
            "display_name": display_name,
            "role": "user", "time": now_str(),
            "text": final_text,
            "room": "guest" if is_guest_room
                    else ("public" if is_public else "private"),
        }
        if not is_public and not is_guest_room:
            msg["to"] = selected_key
        if st.session_state.reply_to:
            msg["reply_to"] = st.session_state.reply_to
        chat_all.append(msg)
        if len(chat_all) > MAX_CHAT_ENTRIES:
            chat_all[:] = chat_all[-MAX_CHAT_ENTRIES:]
        ok, new_sha = save_github_file(CHAT_FILE, chat_all, chat_sha, f"msg {display_name}")
        if ok:
            st.session_state.reply_to = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════
#  BOTTOM INFO
# ═══════════════════════════════════════════════════════════════
with st.expander("⚙️ " + L["info"], expanded=False):
    st.caption(f"{APP_NAME} · v{APP_VERSION}")
    if is_public and not is_guest:
        if st.button("🗑️ " + L["clear_chat"], key="clear_btn"):
            ok, _ = save_github_file(CHAT_FILE, [], chat_sha, "clear")
            if ok:
                st.success(L["success_clear"])
                st.rerun()
    if is_guest_room:
        st.caption("💡 " + L["guest_note"])
