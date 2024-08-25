import base64
import enum
import io
import json
import os
import subprocess
import pprint
import logging
from base64 import b64encode, b64decode
from datetime import datetime
from io import BytesIO
from json import JSONEncoder

import numpy as np
import requests
import torch
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger("[auto-msg_realtime]")

# log.setLevel(logging.INFO)
# Logging
lin_notify_history_array = [['', '', '']]
telegram_bot_history_array = [['', '', '']]
discord_bot_history_array = [['', '', '']]


def tensor_to_pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def image_to_base64(image):
    pli_image = tensor_to_pil(image)
    image_data = io.BytesIO()
    pli_image.save(image_data, format='PNG', pnginfo=None)
    image_data_bytes = image_data.getvalue()
    encoded_image = "" + base64.b64encode(image_data_bytes).decode('utf-8')
    # encoded_image = "data:image/png;base64," + base64.b64encode(image_data_bytes).decode('utf-8')
    return encoded_image


class EnumSendImageResult(enum.Enum):
    ALL = 'SD-Image-All'
    ONLY_GRID = 'Grid-Image-only'
    NO_GRID = 'Each-Image-noGrid'

    @classmethod
    def values(cls):
        return [e.value for e in cls]


class EnumSendContent(enum.Enum):
    SDIMAGE = 'SD-Image'
    # ScreenShot = 'ScreenShot' # for the developer, if u know what you do, u can enable this by yourself.
    TextPrompt = 'Text-Prompt'
    Text_neg_prompt = 'Text-negPrompt'
    PNG_INFO = 'PNG-INFO(max 4096 characters)'
    SD_INFO = 'SD-INFO(max 4096 characters)'
    Text_Temperature = 'Text-Temperature'

    @classmethod
    def values(cls):
        return [e.value for e in cls]


class EnumTriggetType(enum.Enum):
    SDIMAGE = 'SD-Image-generated'
    TIMER = 'Timer-Countdown'
    STATE_TEMPERATURE_GPU = 'STATE-Temperature-GPU '
    STATE_TEMPERATURE_CPU = 'STATE-Temperature-CPU'

    @classmethod
    def to_dict(cls):
        return {e.name: e.value for e in cls}

    @classmethod
    def items(cls):
        return [(e.name, e.value) for e in cls]

    @classmethod
    def keys(cls):
        return [e.name for e in cls]

    @classmethod
    def values(cls):
        return [e.value for e in cls]


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def base64_decodeX(data: str) -> str:
    data = data.encode("ascii")
    rem = len(data) % 4
    if rem > 0:
        data += b"=" * (4 - rem)
    return base64.urlsafe_b64decode(data).decode('utf-8')


def send_msg_all_lets_go(trigger_any_type, trigger_append_image,
                         enable_im_line_notify, enable_im_telegram, enable_im_discord,
                         im_line_notify_token, im_line_notify_msg_header,
                         im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                         im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header,
                         prompt, extra_pnginfo,
                         msg_png_info_enabled, msg_pos_prompt_enabled, msg_neg_prompt_enabled):
    # pprint.pprint(prompt, width=1)
    # pprint.pprint(extra_pnginfo, width=1)

    log.warning("[][Auto-Msg][send_msg_all_lets_go]  extra_pnginfo="  )
    opened_files = []
    opened_files_path = []
    base_folder = os.path.dirname(__file__)
    image_path = os.path.join(base_folder, 'decade.png')

    image_64 = image_to_base64(trigger_append_image)
    image_64_decode = base64.b64decode(image_64)
    image_result = open(image_path, 'wb')
    image_result.write(image_64_decode)

    image = open(image_path, 'rb')
    opened_files.append(image)
    opened_files_path.append(image_path)

    im_line_notify_msg_header += '\n▣prompt:'+json.dumps(prompt)[:500]
    im_telegram_msg_header += '\n▣prompt:'+json.dumps(prompt)[:500]
    im_discord_msg_header += '\n▣prompt:'+json.dumps(prompt)[:500]

    if enable_im_line_notify:
        result_line_notify = send_msg_linenotify(opened_files, im_line_notify_token, im_line_notify_msg_header)
        log.warning(f"[][send_msg_all][result_line_notify]: {result_line_notify}")

    if enable_im_telegram:
        result_telegram_bot = send_msg_telegram(opened_files, im_telegram_token_botid,
                                                im_telegram_token_chatid,
                                                im_telegram_msg_header)
        log.warning(f"[][send_msg_all][result_telegram_bot]: {result_telegram_bot}")
    if enable_im_discord:
        result_discord_bot = send_msg_discord(opened_files, opened_files_path, im_discord_token_botid,
                                              im_discord_token_chatid,
                                              im_discord_msg_header)
        log.warning(f"[][send_msg_all][result_discord_bot]: {result_discord_bot}")

    return {'setting': [lin_notify_history_array[0], telegram_bot_history_array[0],
                        discord_bot_history_array[0]],
            'line': lin_notify_history_array[0],
            'telegram': telegram_bot_history_array[0],
            'discord': discord_bot_history_array[0]}


def send_msg_discord(opened_files, opened_files_path, im_discord_token_botid, im_discord_token_chatid,
                     im_discord_msg_header):
    log.warning("[2][Auto-Msg][send_msg_discord] " + im_discord_msg_header)

    # https://discord.com/developers/docs/resources/message
    im_discord_token_botid = str(im_discord_token_botid or '').strip()
    im_discord_token_chatid = str(im_discord_token_chatid or '').strip()
    im_discord_msg_header = str(im_discord_msg_header or '').strip()
    log.warning(
        f"[][starting][send_msg_discord]: {im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header}")
    url = f"https://discord.com/api/v10/channels/{im_discord_token_chatid}/messages"

    payload = {}
    result = ''
    try:
        if len(opened_files_path) > 0:
            headers = {"Authorization": 'Bot ' + im_discord_token_botid,
                       }
            payload = {"content": im_discord_msg_header,  # https://discord.com/developers/docs/reference#uploading-files
                       "message_reference": {
                           "message_id": "233648473390448641"
                       },

                       }
            json_arr = []
            img_seek_0_obj = {}
            for index, img_path in enumerate(opened_files_path):
                filename = os.path.basename(img_path)
                opened_files[index].seek(0)
                img_seek_0_obj[filename] = opened_files[index].read()
                json_arr.append({
                    "id": index,
                    "description": filename,
                    "filename": filename,
                    "title": filename,
                    "image": {
                        # "url": "https://www.decade.tw/wp-content/uploads/2021/09/DECADE_new.png"
                        "url": "attachment://" + filename
                    },
                    "thumbnail": {
                        "url": "attachment://" + filename
                    },

                }
                )

            payload['attachments'] = json_arr
            payload['embeds'] = json_arr
            post_json = json.dumps(payload)
            log.warning(f"[][starting][send_msg_discord][post_json]: {post_json}")
            result = requests.post(url, headers=headers, json=post_json, files=img_seek_0_obj)
            log.warning(f"[][][send_msg_discord]w/image: {result}")

        headers = {"Authorization": 'Bot ' + im_discord_token_botid,
                   "Content-Type": "application/json",
                   # "Content-Type": 'multipart/form-data'
                   # "Content-Type": 'application/x-www-form-urlencoded'
                   }
        payload = {"content": im_discord_msg_header, "tts": 'false'}
        post_json = json.dumps(payload)
        result = requests.post(url, headers=headers, data=post_json).text
        # result = requests.post(url, headers=headers, data=data, files=imagefile)
    except Exception as e:
        result = str(e)
    discord_bot_history_array.append(['', result, im_discord_msg_header])
    if len(discord_bot_history_array) > 3:
        discord_bot_history_array.remove(discord_bot_history_array[0])

    return discord_bot_history_array


def send_msg_linenotify(opened_files, im_line_notify_token, im_line_notify_msg_header):
    log.warning("[2][Auto-Msg][send_msg_discord] " + im_line_notify_msg_header)

    im_line_notify_token = str(im_line_notify_token or '').strip()
    im_line_notify_msg_header = str(im_line_notify_msg_header or '').strip()
    log.warning(
        f"[][starting][send_msg_linenotify]: {opened_files, im_line_notify_token, im_line_notify_msg_header}")
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': 'Bearer ' + im_line_notify_token
    }
    data = {
        'message': im_line_notify_msg_header
    }
    result = ''
    try:
        if len(opened_files) > 0:
            for img in opened_files:
                img.seek(0)
                imagefile = {'imageFile': img}
                result = requests.post(url, headers=headers, data=data, files=imagefile)
                log.warning(f"[][][send_msg_linenotify]w/image: {result}")

        else:
            result = requests.post(url, headers=headers, data=data)
            log.warning(f"[][][send_msg_linenotify]w/text: {result}")
        result = str(result.text)
    except Exception as e:
        result = str(e)

    lin_notify_history_array.append(['', result, im_line_notify_msg_header])
    if len(lin_notify_history_array) > 3:
        lin_notify_history_array.remove(lin_notify_history_array[0])
    return lin_notify_history_array



def send_msg_telegram(opened_files, im_telegram_token_botid, im_telegram_token_chatid,
                      im_telegram_msg_header):
    log.warning("[2][Auto-Msg][send_msg_telegram] " + im_telegram_msg_header)

    im_telegram_token_botid = str(im_telegram_token_botid or '').strip()
    im_telegram_token_chatid = str(im_telegram_token_chatid or '').strip()
    im_telegram_msg_header = str(im_telegram_msg_header or '').strip()

    # log.warning(f"[][starting][send_msg_telegram]: {opened_files, im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header}")

    assert type(im_telegram_msg_header) == str, "must be str"

    # im_telegram_msg_header = trim_string(str(im_telegram_msg_header), 1000, '...(tele img caption max len=4096)')
    # log.warning(f"[1][][send_msg_telegram]im_telegram_msg_header: {im_telegram_msg_header}")
    ori_str = im_telegram_msg_header
    if len(ori_str) > 800:
        log.warning(
            f"[][][send_msg_telegram]img caption too long >800 send append send text alternative: {im_telegram_msg_header}")
        im_telegram_msg_header = "[send from web-ui] Image Caption Too Long; send text msg alternative"
        # im_telegram_msg_header = im_telegram_msg_header[:800]+'...(tele img caption max len=4096)'

    # msg_all = bot_telegram_msg_header + str(bot_line_notify_trigger_by) + str(bot_line_notify_send_with)
    headers = {'Content-Type': 'application/json', "cache-control": "no-cache"}
    result = ''
    # API ref: https://core.telegram.org/bots/api#sendphoto
    try:
        if len(opened_files) > 0:
            url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendPhoto'
            data = {"chat_id": im_telegram_token_chatid, "caption": im_telegram_msg_header}
            for img in opened_files:
                img.seek(0)
                imagefile = {'photo': img}
                # result = requests.post(url, headers=headers, data=json.dumps(data), files=imagefile)
                result = requests.post(url, params=data, files=imagefile)
                log.warning(f"[][][send_msg_telegram]w/image: {result}")
            if len(ori_str) > 800:
                url2 = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendMessage'
                data2 = {"chat_id": im_telegram_token_chatid, "text": ori_str}
                log.warning(f"[][][send_msg_telegram]data: {data2}")
                result2 = requests.post(url2, params=data2)
                log.warning(f"[][][send_msg_telegram]w/text: {result2}")

        else:
            # url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendMessage?chat_id={im_telegram_token_chatid}&text={im_telegram_msg_header}'
            # result = requests.get(url)
            url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendMessage'
            data = {"chat_id": im_telegram_token_chatid, "text": im_telegram_msg_header}
            log.warning(f"[][][send_msg_telegram]data: {data}")
            # result = requests.post(url, headers=headers, data=data, json=json.dumps(data))
            result = requests.post(url, params=data)
            log.warning(f"[][][send_msg_telegram]w/text: {result}")

        result = str(result.text)
    except Exception as e:
        result = str(e)
    telegram_bot_history_array.append(['', result, im_telegram_msg_header])
    if len(telegram_bot_history_array) > 3:
        telegram_bot_history_array.remove(telegram_bot_history_array[0])
    log.warning(f"[][][send_msg_telegram]: {result}")
    return telegram_bot_history_array

class AutoMsgLINE:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "enable_im_discord": ([True, False],),
                "im_discord_token_botid": ("STRING", {"multiline": False,
                                                      "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_discord_token_chatid": ("STRING", {"multiline": False, "default": "1274866471884816395"}),
                "im_discord_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-discord]"}),
                "enable_im_telegram": ([True, False],),
                "im_telegram_token_botid": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_telegram_token_chatid": ("STRING", {"multiline": False, "default": "1967680189"}),
                "im_telegram_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-telegram]"}),
            },
            "optional": {
                "trigger_any_type": ("*",),
                "trigger_append_image": ("IMAGE",),
            },
            "required": {


                "enable_im_line_notify": ([True, False],),
                "msg_png_info_enabled": ([True, False],),
                "msg_pos_prompt_enabled": ([True, False],),
                "msg_neg_prompt_enabled": ([True, False],),
                "im_line_notify_token": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_line_notify_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-line]"}),
            }
        }

    RETURN_TYPES = ("*", "IMAGE", "STRING", "STRING", "STRING",)
    RETURN_NAMES = (
    "output-original-input", "output-original-input-IMAGE", "🌀output-text-LINE", "🌀output-text-Telegram",
    "🌀output-text-Discord",)
    FUNCTION = "call_all"
    CATEGORY = "🧩 Auto-Msg-Realtime"

    def call_all(self, trigger_any_type=None, trigger_append_image=None,
                 enable_im_line_notify=False, enable_im_telegram=False,
                 enable_im_discord=False,
                 im_line_notify_token='xxx', im_line_notify_msg_header='xxx',
                 im_telegram_token_botid='xxx', im_telegram_token_chatid='xxx', im_telegram_msg_header='xxx',
                 im_discord_token_botid='xxx', im_discord_token_chatid='xxx', im_discord_msg_header='xxx',
                 prompt=None, extra_pnginfo=None,
                 msg_png_info_enabled=False, msg_pos_prompt_enabled=False, msg_neg_prompt_enabled=False):
        # enable_im_line_notify = False
        # enable_im_telegram = False
        # enable_im_discord = False
        result = send_msg_all_lets_go(trigger_any_type, trigger_append_image,
                                      enable_im_line_notify, enable_im_telegram,
                                      enable_im_discord,
                                      im_line_notify_token, im_line_notify_msg_header,
                                      im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                                      im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header,
                                      prompt, extra_pnginfo,
                                      msg_png_info_enabled, msg_pos_prompt_enabled, msg_neg_prompt_enabled)
        log.warning("[9][AutoMsgLINE][]" + im_line_notify_msg_header)

        return trigger_any_type,trigger_append_image, result.get('line'), result.get('telegram'), result.get('discord'),

class AutoMsgTelegram:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "enable_im_line_notify": ([True, False],),
                "im_line_notify_token": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_line_notify_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-line]"}),
                "enable_im_discord": ([True, False],),
                "im_discord_token_botid": ("STRING", {"multiline": False,
                                                      "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_discord_token_chatid": ("STRING", {"multiline": False, "default": "1274866471884816395"}),
                "im_discord_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-discord]"}),
            },
            "optional": {
                "trigger_any_type": ("*",),
                "trigger_append_image": ("IMAGE",),
            },
            "required": {


                "enable_im_telegram": ([True, False],),
                "msg_png_info_enabled": ([True, False],),
                "msg_pos_prompt_enabled": ([True, False],),
                "msg_neg_prompt_enabled": ([True, False],),
                "im_telegram_token_botid": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_telegram_token_chatid": ("STRING", {"multiline": False, "default": "1967680189"}),
                "im_telegram_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-telegram]"}),
            }
        }

    RETURN_TYPES = ("*", "IMAGE", "STRING", "STRING", "STRING",)
    RETURN_NAMES = (
    "output-original-input", "output-original-input-IMAGE", "🌀output-text-LINE", "🌀output-text-Telegram",
    "🌀output-text-Discord",)
    FUNCTION = "call_all"
    CATEGORY = "🧩 Auto-Msg-Realtime"

    def call_all(self, trigger_any_type=None, trigger_append_image=None,
                 enable_im_line_notify=False, enable_im_telegram=False,
                 enable_im_discord=False,
                 im_line_notify_token='xxx', im_line_notify_msg_header='xxx',
                 im_telegram_token_botid='xxx', im_telegram_token_chatid='xxx', im_telegram_msg_header='xxx',
                 im_discord_token_botid='xxx', im_discord_token_chatid='xxx', im_discord_msg_header='xxx',
                 prompt=None, extra_pnginfo=None,
                 msg_png_info_enabled=False, msg_pos_prompt_enabled=False, msg_neg_prompt_enabled=False):
        # enable_im_line_notify = False
        # enable_im_telegram = False
        # enable_im_discord = False
        result = send_msg_all_lets_go(trigger_any_type, trigger_append_image,
                                      enable_im_line_notify, enable_im_telegram,
                                      enable_im_discord,
                                      im_line_notify_token, im_line_notify_msg_header,
                                      im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                                      im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header,
                                      prompt, extra_pnginfo,
                                      msg_png_info_enabled, msg_pos_prompt_enabled, msg_neg_prompt_enabled)
        log.warning("[9][AutoMsgTelegram][]" + im_line_notify_msg_header)

        return trigger_any_type,trigger_append_image, result.get('line'), result.get('telegram'), result.get('discord'),

class AutoMsgDiscord:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "enable_im_line_notify": ([True, False],),
                "enable_im_telegram": ([True, False],),
                "im_line_notify_token": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_line_notify_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-line]"}),

                "im_telegram_token_botid": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_telegram_token_chatid": ("STRING", {"multiline": False, "default": "1967680189"}),
                "im_telegram_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-telegram]"}),
            },
            "optional": {
                "trigger_any_type": ("*",),
                "trigger_append_image": ("IMAGE",),
            },
            "required": {


                "enable_im_discord": ([True, False],),

                "msg_png_info_enabled": ([True, False],),
                "msg_pos_prompt_enabled": ([True, False],),
                "msg_neg_prompt_enabled": ([True, False],),



                "im_discord_token_botid": ("STRING", {"multiline": False,
                                                      "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_discord_token_chatid": ("STRING", {"multiline": False, "default": "1274866471884816395"}),
                "im_discord_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-discord]"}),

            }
        }

    RETURN_TYPES = ("*", "IMAGE", "STRING", "STRING", "STRING",)
    RETURN_NAMES = (
    "output-original-input", "output-original-input-IMAGE", "🌀output-text-LINE", "🌀output-text-Telegram",
    "🌀output-text-Discord",)
    FUNCTION = "call_all"
    CATEGORY = "🧩 Auto-Msg-Realtime"

    def call_all(self, trigger_any_type=None, trigger_append_image=None,
                 enable_im_line_notify=False, enable_im_telegram=False,
                 enable_im_discord=False,
                 im_line_notify_token='xxx', im_line_notify_msg_header='xxx',
                 im_telegram_token_botid='xxx', im_telegram_token_chatid='xxx', im_telegram_msg_header='xxx',
                 im_discord_token_botid='xxx', im_discord_token_chatid='xxx', im_discord_msg_header='xxx',
                 prompt=None, extra_pnginfo=None,
                 msg_png_info_enabled=False, msg_pos_prompt_enabled=False, msg_neg_prompt_enabled=False):
        # enable_im_line_notify = False
        # enable_im_telegram = False
        # enable_im_discord = False
        result = send_msg_all_lets_go(trigger_any_type, trigger_append_image,
                                      enable_im_line_notify, enable_im_telegram,
                                      enable_im_discord,
                                      im_line_notify_token, im_line_notify_msg_header,
                                      im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                                      im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header,
                                      prompt, extra_pnginfo,
                                      msg_png_info_enabled, msg_pos_prompt_enabled, msg_neg_prompt_enabled)
        log.warning("[9][AutoMsgDiscord][]" + im_line_notify_msg_header)

        return trigger_any_type,trigger_append_image, result.get('line'), result.get('telegram'), result.get('discord'),


class AutoMsgALL:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",

            },
            "optional": {
                "trigger_any_type": ("*",),

                "trigger_append_image": ("IMAGE",),
            },
            "required": {

                "enable_im_line_notify": ([True, False],),
                "enable_im_telegram": ([True, False],),
                "enable_im_discord": ([True, False],),

                "msg_png_info_enabled": ([True, False],),
                "msg_pos_prompt_enabled": ([True, False],),
                "msg_neg_prompt_enabled": ([True, False],),

                "im_line_notify_token": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_line_notify_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-line]"}),

                "im_telegram_token_botid": (
                    "STRING", {"multiline": False, "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_telegram_token_chatid": ("STRING", {"multiline": False, "default": "1967680189"}),
                "im_telegram_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-telegram]"}),

                "im_discord_token_botid": ("STRING", {"multiline": False,
                                                      "default": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"}),
                "im_discord_token_chatid": ("STRING", {"multiline": False, "default": "1274866471884816395"}),
                "im_discord_msg_header": ("STRING", {"multiline": True, "default": "[from-ComfyUI-discord]"}),

            }
        }

    RETURN_TYPES = ("*", "IMAGE", "STRING", "STRING", "STRING",)
    RETURN_NAMES = ("output-original-input", "output-original-input-IMAGE","🌀output-text-LINE", "🌀output-text-Telegram", "🌀output-text-Discord",)
    FUNCTION = "call_all"
    CATEGORY = "🧩 Auto-Msg-Realtime"

    def call_all(self, trigger_any_type=None, trigger_append_image=None,
                 enable_im_line_notify=False, enable_im_telegram=False,
                 enable_im_discord=False,
                 im_line_notify_token='xxx', im_line_notify_msg_header='xxx',
                 im_telegram_token_botid='xxx', im_telegram_token_chatid='xxx', im_telegram_msg_header='xxx',
                 im_discord_token_botid='xxx', im_discord_token_chatid='xxx', im_discord_msg_header='xxx',
                 prompt=None, extra_pnginfo=None,
                 msg_png_info_enabled=False, msg_pos_prompt_enabled=False, msg_neg_prompt_enabled=False):
        # enable_im_line_notify = False
        # enable_im_telegram = False
        # enable_im_discord = False
        result = send_msg_all_lets_go(trigger_any_type,trigger_append_image,
                                      enable_im_line_notify, enable_im_telegram,
                                      enable_im_discord,
                                      im_line_notify_token, im_line_notify_msg_header,
                                      im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                                      im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header,
                                      prompt, extra_pnginfo,
                                      msg_png_info_enabled, msg_pos_prompt_enabled, msg_neg_prompt_enabled)
        log.warning("[9][AutoMsgALL][]" + im_line_notify_msg_header)

        return trigger_any_type,trigger_append_image, result.get('line'), result.get('telegram'), result.get('discord'),

    # def __init__(self):
    #     up_2_level_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    #
    #     f=folder_names_and_paths["custom_nodes"]
    #     comfy_path = os.path.dirname(folder_paths.__file__)
    #     custom_nodes_path = os.path.join(comfy_path, 'custom_nodes')
    #     self.output_dir = folder_paths.get_temp_directory()
    #     self.type = "temp"
    #     self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for x in range(5))
    #     self.compress_level = 1
