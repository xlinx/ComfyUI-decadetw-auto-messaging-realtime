"""
    .___                        .___           __
  __| _/____   ____ _____     __| _/____     _/  |___  _  __
 / __ |/ __ \_/ ___\\__  \   / __ |/ __ \    \   __\ \/ \/ /
/ /_/ \  ___/\  \___ / __ \_/ /_/ \  ___/     |  |  \     /
\____ |\___  >\___  >____  /\____ |\___  > /\ |__|   \/\_/
     \/    \/     \/     \/      \/    \/  \/
   _____          __           .____    .____       _____
  /  _  \  __ ___/  |_  ____   |    |   |    |     /     \
 /  /_\  \|  |  \   __\/  _ \  |    |   |    |    /  \ /  \
/    |    \  |  /|  | (  <_> ) |    |___|    |___/    Y    \
\____|__  /____/ |__|  \____/  |_______ \_______ \____|__  /
        \/                             \/       \/       \/
             · -—+ auto-prompt-llm-text-vision Extension for ComfyUI +—- ·
             Auto Msg realtime | LINE | Telegram | Discord
             https://decade.tw
             https://github.com/Suzie1/ComfyUI_Guide_To_Making_Custom_Nodes/wiki/init-file
"""


from .auto_msg_realtime import *

NODE_CLASS_MAPPINGS = {
    "Auto-MSG-ALL":          AutoMsgALL,
    "Auto-MSG-Line-Notify":  AutoMsgLINE,
    "Auto-MSG-Telegram-Bot": AutoMsgTelegram,
    "Auto-MSG-Discord-Bot":  AutoMsgDiscord,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "Auto-MSG-ALL":           "💬 Auto-MSG-ALL",
    "Auto-MSG-Line-Notify":   "💬 Auto-MSG-Line-Notify",
    "Auto-MSG-Telegram-Bot":  "💬 Auto-MSG-Telegram-Bot",
    "Auto-MSG-Discord-Bot":   "💬 Auto-MSG-Discord-Bot"
}
print("[0][Auto-Msg-Realtime][]")
