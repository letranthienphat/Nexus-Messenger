"""
LTTP Messenger - Fast UI Edition
=================================
Modern chat app built on Streamlit + GitHub as backend.
Features: real-time fragments, glassmorphism UI, emoji, reply, search,
          unread badges, session timeout, retry-safe GitHub writes.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import hashlib
import time
import re
from github import Github, GithubException
from datetime import datetime, timedelta
import zoneinfo

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
APP_NAME = "LTTP Messenger"
APP_VERSION = "3.0.0 (Fast UI)"
MAX_FILE_MB = 25
MAX_CHAT_ENTRIES = 800          # giữ N tin gần nhất để tránh file phình to
SESSION_TIMEOUT_MIN = 60        # tự logout sau N phút không hoạt động
REFRESH_INTERVAL = "4s"         # fragment auto-refresh

# ═══════════════════════════════════════════════════════════════
#  i18n
# ═══════════════════════════════════════════════════════════════
LANGUAGES = {
    "Tiếng Việt": {
        "app_tagline": "Trò chuyện nhanh, bảo mật, không giới hạn.",
        "login": "Đăng nhập", "register": "Đăng ký", "logout": "Đăng xuất",
        "username": "Tên đăng nhập", "password": "Mật khẩu",
        "new_password": "Mật khẩu mới", "confirm_password": "Xác nhận mật khẩu",
        "btn_login": "🔓 Đăng nhập", "btn_register": "✨ Tạo tài khoản",
        "err_missing": "Vui lòng nhập đầy đủ thông tin.",
        "err_wrong": "Sai tên đăng nhập hoặc mật khẩu.",
        "err_match": "Mật khẩu xác nhận không khớp.",
        "err_exist": "Tên đăng nhập đã tồn tại.",
        "err_username_invalid": "Tên đăng nhập chỉ chứa chữ, số, dấu _ (3-24 ký tự).",
        "err_password_short": "Mật khẩu phải từ 6 ký tự.",
        "success_register": "Đăng ký thành công! Hãy đăng nhập.",
        "welcome": "Chào mừng trở lại",
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
        "chat_placeholder": "Nhập tin nhắn... (Enter để gửi)",
        "attach": "Đính kèm",
        "send_file": "Gửi tệp",
        "err_file_size": f"Tệp vượt quá {MAX_FILE_MB}MB.",
        "uploading": "Đang tải lên...",
        "err_not_friend": "Bạn không thể nhắn tin với người này.",
        "clear_chat": "Xóa lịch sử",
        "success_clear": "Đã xóa lịch sử.",
        "no_messages": "Chưa có tin nhắn nào. Hãy bắt đầu cuộc trò chuyện!",
        "typing": "đang nhập...",
        "online": "Đang hoạt động",
        "search": "Tìm kiếm tin nhắn...",
        "info": "Thông tin",
        "reply": "Trả lời",
        "cancel_reply": "Hủy trả lời",
        "session_expired": "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        "missing_secrets": "Thiếu cấu hình Secrets (DB_GITHUB_TOKEN, DB_REPO_NAME).",
        "emoji": "Cảm xúc",
        "online_users": "Đang online",
    },
    "English": {
        "app_tagline": "Fast, secure, unlimited chat.",
        "login": "Login", "register": "Register", "logout": "Logout",
        "username": "Username", "password": "Password",
        "new_password": "New password", "confirm_password": "Confirm password",
        "btn_login": "🔓 Sign in", "btn_register": "✨ Create account",
        "err_missing": "Please fill in all fields.",
        "err_wrong": "Incorrect username or password.",
        "err_match": "Passwords do not match.",
        "err_exist": "Username already exists.",
        "err_username_invalid": "Username: letters, digits, _ (3-24 chars).",
        "err_password_short": "Password must be at least 6 characters.",
        "success_register": "Registered! Please sign in.",
        "welcome": "Welcome back",
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
        "chat_placeholder": "Type a message... (Enter to send)",
        "attach": "Attach",
        "send_file": "Send file",
        "err_file_size": f"File exceeds {MAX_FILE_MB}MB.",
        "uploading": "Uploading...",
        "err_not_friend": "You cannot chat with this user.",
        "clear_chat": "Clear history",
        "success_clear": "History cleared.",
        "no_messages": "No messages yet. Start the conversation!",
        "typing": "is typing...",
        "online": "Online",
        "search": "Search messages...",
        "info": "Info",
        "reply": "Reply",
        "cancel_reply": "Cancel reply",
        "session_expired": "Session expired. Please sign in again.",
        "missing_secrets": "Missing secrets (DB_GITHUB_TOKEN, DB_REPO_NAME).",
        "emoji": "Emoji",
        "online_users": "Online now",
    },
}
L = LANGUAGES[st.session_state.get("lang", "Tiếng Việt")] if "lang" in st.session_state else LANGUAGES["Tiếng Việt"]

# ═══════════════════════════════════════════════════════════════
#  PAGE CONFIG & FAST UI CSS
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title=APP_NAME, page_icon="💬", layout="wide",
    initial_sidebar_state="expanded"
)

FAST_UI_CSS = """
<style>
/* ---------- BASE ---------- */
:root{
  --bg:#0b1020; --bg2:#101733; --card:rgba(255,255,255,.06);
  --border:rgba(255,255,255,.12); --text:#e9ecf5; --muted:#9aa3bd;
  --accent:#7c5cff; --accent2:#22d3ee; --success:#22c55e; --danger:#ef4444;
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
.block-container{padding-top:1.2rem;padding-bottom:4.5rem;max-width:1150px;}

/* ---------- SCROLLBAR ---------- */
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:8px}

/* ---------- INPUTS ---------- */
.stTextInput input,.stTextArea textarea{
  background:var(--card)!important;border:1px solid var(--border)!important;
  color:var(--text)!important;border-radius:12px!important;padding:10px 12px!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 2px rgba(124,92,255,.25)!important;
}

/* ---------- BUTTONS ---------- */
.stButton>button{
  background:var(--card);border:1px solid var(--border);color:var(--text);
  border-radius:12px;font-weight:600;transition:all .18s ease;
}
.stButton>button:hover{
  transform:translateY(-1px);
  border-color:var(--accent);
  box-shadow:0 6px 20px rgba(124,92,255,.25);
}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  border:none;color:#fff;
}

/* ---------- TABS ---------- */
.stTabs [data-baseweb="tab-list"]{gap:6px;background:transparent}
.stTabs [data-baseweb="tab"]{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:8px 16px;color:var(--muted);
}
.stTabs [aria-selected="true"]{
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:#fff!important;border-color:transparent!important;
}

/* ---------- CHAT BUBBLES ---------- */
[data-testid="stChatMessage"]{
  background:var(--bubble-other);
  border:1px solid var(--border);
  border-radius:16px;
  padding:10px 14px;
  margin-bottom:8px;
  backdrop-filter:blur(8px);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]){
  background:var(--bubble-me);
  border-color:transparent;
}
/* reply preview */
.reply-preview{
  border-left:3px solid var(--accent);
  padding:4px 10px;margin:4px 0 8px 0;
  background:rgba(124,92,255,.1);border-radius:6px;font-size:.85rem;color:var(--muted);
}

/* ---------- GLASS CARD ---------- */
.glass{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:16px 20px;backdrop-filter:blur(12px);
}

/* ---------- HERO ---------- */
.hero{
  text-align:center;padding:26px 16px 8px 16px;
}
.hero h1{
  font-size:2.4rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,#fff,#a5b4fc 60%,#22d3ee);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  margin-bottom:6px;
}
.hero p{color:var(--muted);font-size:1rem}

/* ---------- AVATAR ---------- */
.avatar{
  width:38px;height:38px;border-radius:50%;display:inline-flex;
  align-items:center;justify-content:center;font-weight:700;color:#fff;
  background:linear-gradient(135deg,#7c5cff,#22d3ee);
  flex:0 0 38px;font-size:.9rem;
}
.dot-online{
  display:inline-block;width:8px;height:8px;border-radius:50%;
  background:var(--success);margin-right:6px;
  box-shadow:0 0 8px var(--success);
}

/* ---------- SIDEBAR ---------- */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#0d1224,#0b1020);
  border-right:1px solid var(--border);
}
[data-testid="stSidebar"] .block-container{padding-top:1rem;}

/* ---------- CHAT ROOM HEADER ---------- */
.room-header{
  display:flex;align-items:center;gap:12px;
  padding:12px 16px;border-radius:16px;
  background:var(--card);border:1px solid var(--border);
  margin-bottom:12px;
}
.room-header h3{margin:0;font-size:1.15rem}
.room-header small{color:var(--muted)}

/* ---------- UNREAD BADGE ---------- */
.badge{
  background:var(--danger);color:#fff;border-radius:10px;
  padding:1px 7px;font-size:.7rem;font-weight:700;margin-left:6px;
}

/* ---------- FILE PREVIEW ---------- */
.file-chip{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(124,92,255,.15);border:1px solid var(--accent);
  border-radius:10px;padding:6px 12px;margin:4px 0;font-size:.85rem;
}

/* ---------- CHAT INPUT ---------- */
[data-testid="stChatInput"] textarea{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:16px!important;color:var(--text)!important;
}

/* ---------- METRIC ---------- */
[data-testid="stMetricValue"]{color:var(--text);}
</style>
"""
st.markdown(FAST_UI_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "lang": "Tiếng Việt",
        "logged_in": False,
        "username": "",
        "client_timezone": "Asia/Ho_Chi_Minh",
        "last_activity": time.time(),
        "reply_to": None,
        "search_query": "",
        "last_seen_chat": {},
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

init_state()

# Nếu đổi ngôn ngữ → refresh L
L = LANGUAGES[st.session_state.lang]

# ═══════════════════════════════════════════════════════════════
#  TIMEZONE DETECTION
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
    content = json.dumps(data, ensure_ascii=False, indent=2)
    for attempt in range(retries):
        try:
            if sha:
                repo.update_file(path, message, content, sha, branch=BRANCH)
            else:
                repo.create_file(path, message, content, branch=BRANCH)
            return True
        except GithubException as e:
            if e.status in (409, 422) and attempt < retries - 1:
                time.sleep(0.4 * (attempt + 1))
                try:
                    sha = repo.get_contents(path, ref=BRANCH).sha
                except Exception:
                    sha = None
                continue
            st.error(f"Save error ({path}): {e}")
            return False
        except Exception as e:
            st.error(f"Save error ({path}): {e}")
            return False
    return False

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
    return (name[:2] if name else "??").upper()

def activity_tick():
    st.session_state.last_activity = time.time()

def check_session():
    if st.session_state.logged_in:
        idle = time.time() - st.session_state.last_activity
        if idle > SESSION_TIMEOUT_MIN * 60:
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.warning(L["session_expired"])
            st.rerun()

def validate_username(u):
    return bool(re.match(r"^[A-Za-z0-9_]{3,24}$", u))

def is_online(user_last_seen_ts):
    try:
        return (time.time() - float(user_last_seen_ts)) < 300  # 5 phút
    except Exception:
        return False

# ═══════════════════════════════════════════════════════════════
#  SIDEBAR TOP (Language + Clock)
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
#  LOGIN / REGISTER (HERO UI)
# ═══════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.markdown(f"""
    <div class="hero">
      <h1>{APP_NAME}</h1>
      <p>{L['app_tagline']}</p>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        tab_login, tab_reg = st.tabs([f"🔑 {L['login']}", f"📝 {L['register']}"])
        accounts, acc_sha = load_github_file(USER_FILE)

        with tab_login:
            u = st.text_input(L["username"], key="li_u")
            p = st.text_input(L["password"], type="password", key="li_p")
            if st.button(L["btn_login"], use_container_width=True, type="primary"):
                if not u or not p:
                    st.warning(L["err_missing"])
                else:
                    h = hash_password(p)
                    found = next((x for x in accounts if x["username"] == u and x["password"] == h), None)
                    if found:
                        st.session_state.logged_in = True
                        st.session_state.username = u
                        activity_tick()
                        st.rerun()
                    else:
                        st.error(L["err_wrong"])

        with tab_reg:
            ru = st.text_input(L["username"], key="rg_u")
            rp = st.text_input(L["new_password"], type="password", key="rg_p")
            rc = st.text_input(L["confirm_password"], type="password", key="rg_c")
            if st.button(L["btn_register"], use_container_width=True, type="primary"):
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
                    if save_github_file(USER_FILE, accounts, acc_sha, f"new user {ru}"):
                        st.success(L["success_register"])
    st.stop()

# ═══════════════════════════════════════════════════════════════
#  LOGGED IN → LOAD DATA
# ═══════════════════════════════════════════════════════════════
check_session()
activity_tick()

accounts, acc_sha = load_github_file(USER_FILE)
chat_all, chat_sha = load_github_file(CHAT_FILE)

me = next((x for x in accounts if x["username"] == st.session_state.username), None)
if not me:
    st.error("Account not found.")
    st.session_state.logged_in = False
    st.rerun()

for k in ("friends", "friend_requests_received", "friend_requests_sent"):
    me.setdefault(k, [])

# cập nhật last_seen mỗi lần mở app (không cần commit mỗi giây)
me["last_seen"] = time.time()

my_friends = me.get("friends", [])
online_friends = [
    f for f in my_friends
    if (lambda u: u and is_online(u.get("last_seen", 0)))(
        next((x for x in accounts if x["username"] == f), None)
    )
]

# ═══════════════════════════════════════════════════════════════
#  SIDEBAR: ACCOUNT + FRIENDS + ROOMS
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div class="glass" style="display:flex;gap:12px;align-items:center;">
      <div class="avatar">{initials(st.session_state.username)}</div>
      <div>
        <div style="font-weight:700;">{st.session_state.username}</div>
        <div style="font-size:.78rem;color:var(--muted);">
          <span class="dot-online"></span>{len(online_friends)} {L['online_users']}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(L["logout"], use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
    st.divider()

    # --- ROOMS ---
    st.markdown(f"#### {L['sidebar_rooms']}")
    room_labels = [L["public_room"]] + [f"💬 {f}" for f in my_friends]
    room_keys = ["__public__"] + my_friends
    selected_idx = st.radio(
        "room", range(len(room_keys)),
        format_func=lambda i: room_labels[i],
        label_visibility="collapsed",
        key="room_select"
    )
    selected_key = room_keys[selected_idx]
    st.divider()

    # --- ADD FRIEND ---
    with st.expander(f"➕ {L['add_friend']}", expanded=False):
        target = st.text_input(L["friend_username"], key="ft_input").strip()
        if st.button(L["btn_send_req"], use_container_width=True):
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
                if save_github_file(USER_FILE, accounts, acc_sha, f"req {target}"):
                    st.success(L["success_friend_sent"])
                    st.rerun()

    # --- PENDING REQUESTS ---
    if me["friend_requests_received"]:
        st.markdown(f"#### 📥 {L['pending_requests']}")
        for sender in list(me["friend_requests_received"]):
            with st.container(border=True):
                st.markdown(f"<div class='avatar' style='width:26px;height:26px;font-size:.7rem;'>{initials(sender)}</div> **{sender}**", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✅", key=f"a_{sender}", use_container_width=True):
                    me["friends"].append(sender)
                    me["friend_requests_received"].remove(sender)
                    sd = next((x for x in accounts if x["username"] == sender), None)
                    if sd:
                        sd.setdefault("friends", []).append(st.session_state.username)
                        if st.session_state.username in sd.get("friend_requests_sent", []):
                            sd["friend_requests_sent"].remove(st.session_state.username)
                    if save_github_file(USER_FILE, accounts, acc_sha, "accept"):
                        st.rerun()
                if c2.button("❌", key=f"d_{sender}", use_container_width=True):
                    me["friend_requests_received"].remove(sender)
                    if save_github_file(USER_FILE, accounts, acc_sha, "decline"):
                        st.rerun()
        st.divider()

    st.caption(f"ℹ️ {APP_NAME} · v{APP_VERSION}")

# ═══════════════════════════════════════════════════════════════
#  MAIN CHAT AREA
# ═══════════════════════════════════════════════════════════════
is_public = selected_key == "__public__"
room_title = L["public_room"] if is_public else f"💬 {selected_key}"

# --- ROOM HEADER ---
if is_public:
    sub = f"{len(my_friends)} {L['friends'].lower()} · {len(online_friends)} {L['online']}"
else:
    sub = f"<span class='dot-online'></span>{L['online']}" if selected_key in online_friends else "offline"

st.markdown(f"""
<div class="room-header">
  <div class="avatar">{'🌐' if is_public else initials(selected_key)}</div>
  <div style="flex:1;">
    <h3>{room_title}</h3>
    <small>{sub}</small>
  </div>
</div>
""", unsafe_allow_html=True)

# --- FILTER MESSAGES ---
if is_public:
    room_msgs = [
        m for m in chat_all
        if m.get("room", "public") == "public"
        and (m["user"] == st.session_state.username or m["user"] in my_friends)
    ]
else:
    room_msgs = [
        m for m in chat_all
        if m.get("room") == "private"
        and ((m["user"] == st.session_state.username and m.get("to") == selected_key)
             or (m["user"] == selected_key and m.get("to") == st.session_state.username))
    ]

# --- SEARCH ---
search = st.text_input("🔍 " + L["search"], key="search_input", label_visibility="visible")
if search:
    q = search.lower()
    room_msgs = [m for m in room_msgs if q in (m.get("text", "") + m.get("user", "")).lower()]

# --- MESSAGE RENDER (fragment = real-time, no full rerun) ---
def render_messages():
    if not room_msgs:
        st.info(L["no_messages"])
        return
    for m in room_msgs:
        is_me = m["user"] == st.session_state.username
        with st.chat_message(m["role"], avatar="🧑" if is_me else "👤"):
            if m.get("reply_to"):
                rp = m["reply_to"]
                st.markdown(
                    f"<div class='reply-preview'>↪ <b>{rp.get('user','')}</b>: {rp.get('text','')[:80]}</div>",
                    unsafe_allow_html=True
                )
            st.markdown(
                f"**{m['user']}** "
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
            # reply button
            if not is_me:
                if st.button("↩ " + L["reply"], key=f"rp_{m.get('time')}_{m['user']}_{id(m)}"):
                    st.session_state.reply_to = {
                        "user": m["user"], "text": m.get("text", "")[:120]
                    }
                    st.rerun()

# Use fragment for real-time refresh (Streamlit >= 1.33)
try:
    @st.fragment(run_every=REFRESH_INTERVAL)
    def live_messages():
        # reload chat from GitHub (cache via sha check)
        fresh, _ = load_github_file(CHAT_FILE)
        if is_public:
            msgs = [m for m in fresh if m.get("room", "public") == "public"
                    and (m["user"] == st.session_state.username or m["user"] in my_friends)]
        else:
            msgs = [m for m in fresh if m.get("room") == "private"
                    and ((m["user"] == st.session_state.username and m.get("to") == selected_key)
                         or (m["user"] == selected_key and m.get("to") == st.session_state.username))]
        if search:
            q = search.lower()
            msgs = [m for m in msgs if q in (m.get("text", "") + m.get("user", "")).lower()]
        if not msgs:
            st.info(L["no_messages"])
            return
        for m in msgs:
            is_me = m["user"] == st.session_state.username
            with st.chat_message(m["role"], avatar="🧑" if is_me else "👤"):
                if m.get("reply_to"):
                    rp = m["reply_to"]
                    st.markdown(
                        f"<div class='reply-preview'>↪ <b>{rp.get('user','')}</b>: {rp.get('text','')[:80]}</div>",
                        unsafe_allow_html=True
                    )
                st.markdown(
                    f"**{m['user']}** "
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

    live_messages()
except AttributeError:
    # Fallback nếu Streamlit cũ
    render_messages()

# ═══════════════════════════════════════════════════════════════
#  REPLY PREVIEW + INPUT
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
        if st.button("✖ " + L["cancel_reply"], use_container_width=True):
            st.session_state.reply_to = None
            st.rerun()

# --- ATTACH + EMOJI + INPUT ---
attach_col, emoji_col, input_col = st.columns([0.5, 0.5, 8])

with attach_col:
    with st.popover("📎", help=L["attach"]):
        up = st.file_uploader(L["attach"], label_visibility="collapsed", key="fup")
        if up is not None:
            fb = up.read()
            mb = len(fb) / (1024 * 1024)
            if mb > MAX_FILE_MB:
                st.error(L["err_file_size"])
            else:
                st.markdown(f"<div class='file-chip'>📄 {up.name} · {mb:.2f} MB</div>",
                            unsafe_allow_html=True)
                if st.button(L["send_file"], use_container_width=True):
                    with st.spinner(L["uploading"]):
                        url = upload_binary(up.name, fb)
                    if url:
                        msg = {
                            "user": st.session_state.username,
                            "role": "user", "time": now_str(),
                            "text": "", "file_url": url, "file_name": up.name,
                            "room": "public" if is_public else "private",
                        }
                        if not is_public:
                            msg["to"] = selected_key
                        chat_all.append(msg)
                        # giới hạn
                        if len(chat_all) > MAX_CHAT_ENTRIES:
                            chat_all[:] = chat_all[-MAX_CHAT_ENTRIES:]
                        if save_github_file(CHAT_FILE, chat_all, chat_sha, "file"):
                            st.success("✅")
                            st.rerun()

with emoji_col:
    with st.popover("😀", help=L["emoji"]):
        emojis = "😀 😂 😍 😎 🤔 😢 😡 👍 👎 ❤️ 🔥 🎉 ✅ ❌ 🚀 💯 👏 🙏 😴 🤝"
        cols = st.columns(6)
        for i, e in enumerate(emojis.split()):
            if cols[i % 6].button(e, key=f"em_{i}"):
                st.session_state.setdefault("pending_emoji", "")
                st.session_state.pending_emoji = e
                st.rerun()

# Chat input
if prompt := st.chat_input(L["chat_placeholder"]):
    msg = {
        "user": st.session_state.username,
        "role": "user", "time": now_str(),
        "text": prompt,
        "room": "public" if is_public else "private",
    }
    if not is_public:
        msg["to"] = selected_key
    if st.session_state.reply_to:
        msg["reply_to"] = st.session_state.reply_to
        st.session_state.reply_to = None
    chat_all.append(msg)
    if len(chat_all) > MAX_CHAT_ENTRIES:
        chat_all[:] = chat_all[-MAX_CHAT_ENTRIES:]
    if save_github_file(CHAT_FILE, chat_all, chat_sha, f"msg {st.session_state.username}"):
        st.rerun()

# ═══════════════════════════════════════════════════════════════
#  BOTTOM: clear chat (public only)
# ═══════════════════════════════════════════════════════════════
if is_public:
    with st.expander("⚙️ " + L["info"], expanded=False):
        st.caption(f"{APP_NAME} · v{APP_VERSION}")
        if st.button("🗑️ " + L["clear_chat"]):
            if save_github_file(CHAT_FILE, [], chat_sha, "clear"):
                st.success(L["success_clear"])
                st.rerun()
