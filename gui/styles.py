"""爱弥斯语音 GUI - 样式定义（微信风格）

配色：微信绿 #95EC69 + 浅灰背景 #EDEDED + 白色消息气泡
"""
from PySide6.QtGui import QColor, QFont

# ===== 微信风格配色 =====
COLOR_WINDOW_BG = "#EDEDED"           # 主窗口背景（浅灰）
COLOR_CHAT_BG = "#F5F5F5"             # 聊天区域背景
COLOR_USER_BUBBLE = "#95EC69"         # 用户气泡（微信绿）
COLOR_USER_BUBBLE_HOVER = "#7FD958"
COLOR_BOT_BUBBLE = "#FFFFFF"          # 爱弥斯气泡（白）
COLOR_BOT_BUBBLE_BORDER = "#E5E5E5"
COLOR_INPUT_BG = "#FFFFFF"            # 输入区背景
COLOR_INPUT_BORDER = "#E0E0E6"        # 输入框边框
COLOR_INPUT_BORDER_FOCUS = "#95EC69"  # 输入框聚焦边框（微信绿）
COLOR_TEXT_PRIMARY = "#000000"
COLOR_TEXT_SECONDARY = "#888888"
COLOR_TEXT_TIMESTAMP = "#B2B2B2"
COLOR_DIVIDER = "#E5E5E5"
COLOR_SEND_BUTTON = "#07C160"         # 微信主绿
COLOR_SEND_BUTTON_HOVER = "#06AD56"
COLOR_SEND_BUTTON_DISABLED = "#BFE9CC"

# 头像背景色（爱弥斯粉金、用户蓝灰）
COLOR_AEMEATH_AVATAR_BG = "#FFD8E5"   # 粉色
COLOR_USER_AVATAR_BG = "#A8D8F0"      # 浅蓝

# 进度条
COLOR_PROGRESS_BAR_BG = "#E0E0E0"
COLOR_PROGRESS_BAR_FG = "#07C160"

# 字体
FONT_FAMILY = "Microsoft YaHei UI, 微软雅黑, Segoe UI, sans-serif"
FONT_SIZE_NORMAL = 14
FONT_SIZE_SMALL = 12
FONT_SIZE_TINY = 11
FONT_SIZE_TITLE = 13

# 气泡圆角
BUBBLE_RADIUS = 8
AVATAR_SIZE = 40


def chat_font(size: int = FONT_SIZE_NORMAL, bold: bool = False) -> QFont:
    f = QFont()
    f.setFamily(FONT_FAMILY.split(",")[0].strip())
    f.setPixelSize(size)
    f.setBold(bold)
    return f


def qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)