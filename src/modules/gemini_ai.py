# Copyright (c) 2025 AshokShau
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
# Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import json
import os
import base64
import time 

from pytdbot import Client, types
from cachetools import TTLCache 

from src.config import OWNER_ID, GEMINI_API_KEY
from src.helpers import get_string
from src.modules.utils import Filter
from src.modules.utils.play_helpers import extract_argument

import google.generativeai as genai
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    if os.environ.get("GEMINI_API_KEY"):
        import logging
        logging.getLogger(__name__).error(f"Gagal mengkonfigurasi Gemini API: {e}")

# Cooldown
COOLDOWN_TIME = 15
user_cooldowns = TTLCache(maxsize=1000, ttl=COOLDOWN_TIME)


@Client.on_message(filters=Filter.command("ask"))
async def ask_gemini(c: Client, message: types.Message) -> None:
    """
    Menangani perintah /ask untuk berinteraksi dengan Gemini AI (hanya teks).
    """
    chat_id = message.chat_id
    user_id = message.from_id
    lang = await c.db.get_lang(chat_id)

    # Cooldown check
    if user_id in user_cooldowns:
        remaining_time = int(user_cooldowns.ttl - (time.time() - user_cooldowns[user_id]))
        await message.reply_text(get_string("cooldown_message", lang).format(remaining_time=remaining_time))
        return

    if not GEMINI_API_KEY:
        await message.reply_text(get_string("gemini_api_key_missing", lang))
        return

    question = extract_argument(message.text)
    
    chat_action_type = "chatActionTyping"
    try:
        await c.invoke({"@type": "sendChatAction", "chat_id": chat_id, "action": {"@type": chat_action_type}})
    except Exception as e:
        c.logger.warning(f"Gagal mengirim status ({chat_action_type}) melalui invoke: {e}")

    try:
        if not question: 
            await message.reply_text(get_string("ask_usage", lang))
            try:
                await c.invoke({"@type": "sendChatAction", "chat_id": chat_id, "action": {"@type": "chatActionCancel"}})
            except Exception as e:
                c.logger.warning(f"Gagal membatalkan status chat action melalui invoke: {e}")
            return

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = await model.generate_content_async(question)

        if response and response.text:
            gemini_response = response.text
            await message.reply_text(f"<b>{get_string('answer', lang)}:</b>\n{gemini_response}")
            user_cooldowns[user_id] = time.time() # Atur cooldown setelah sukses
        else:
            await message.reply_text(get_string("gemini_no_response", lang))

    except Exception as e:
        await message.reply_text(f"{get_string('gemini_error', lang)}: {e}")
        c.logger.error(f"Terjadi kesalahan saat memanggil Gemini API: {e}", exc_info=True)
    finally:
        try:
            await c.invoke({"@type": "sendChatAction", "chat_id": chat_id, "action": {"@type": "chatActionCancel"}})
        except Exception as e:
            c.logger.warning(f"Gagal membatalkan status chat action melalui invoke: {e}")

@Client.on_message(filters=Filter.command("img"))
async def generate_image(c: Client, message: types.Message) -> None:
    """
    Menangani perintah /img untuk menghasilkan gambar menggunakan Gemini AI.
    """
    chat_id = message.chat_id
    user_id = message.from_id
    lang = await c.db.get_lang(chat_id)

    if user_id in user_cooldowns:
        remaining_time = int(user_cooldowns.ttl - (time.time() - user_cooldowns[user_id]))
        await message.reply_text(get_string("cooldown_message", lang).format(remaining_time=remaining_time))
        return

    if not GEMINI_API_KEY:
        await message.reply_text(get_string("gemini_api_key_missing", lang))
        return

    image_prompt = extract_argument(message.text)
    if not image_prompt:
        await message.reply_text(get_string("image_usage", lang))
        return

    try:
        await c.invoke({"@type": "sendChatAction", "chat_id": chat_id, "action": {"@type": "chatActionUploadingPhoto"}})
    except Exception as e:
        c.logger.warning(f"Gagal mengirim status (chatActionUploadingPhoto) melalui invoke: {e}")

    loading_message = await message.reply_text(get_string("generating_image", lang))

    try:
        image_payload = {"instances": {"prompt": image_prompt}, "parameters": {"sampleCount": 1}}
        image_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_API_KEY}"

        image_response_json = await asyncio.to_thread(
            lambda: __import__('requests').post(
                image_api_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(image_payload)
            ).json()
        )

        if image_response_json.get("predictions") and \
           image_response_json["predictions"][0].get("bytesBase64Encoded"):
            
            base64_image = image_response_json["predictions"][0]["bytesBase64Encoded"]
            image_data = base64.b64decode(base64_image)

            temp_image_path = f"database/temp_image_{message.chat_id}_{message.id}.png"
            os.makedirs(os.path.dirname(temp_image_path), exist_ok=True)
            with open(temp_image_path, "wb") as f:
                f.write(image_data)

            await message.reply_photo(
                photo=types.InputFileLocal(temp_image_path),
                caption=f"<b>{get_string('image_result', lang)}:</b> {image_prompt}"
            )
            os.remove(temp_image_path)
            user_cooldowns[user_id] = time.time()
        else:
            await message.reply_text(get_string("image_generation_error", lang))
            c.logger.error(f"API pembuatan gambar tidak mengembalikan data gambar untuk prompt '{image_prompt}': {image_response_json}")

    except Exception as e:
        await message.reply_text(f"{get_string('image_generation_error', lang)}: {e}")
        c.logger.error(f"Terjadi kesalahan saat memanggil API Pembuatan Gambar: {e}", exc_info=True)
    finally:
        await loading_message.delete()
        try:
            await c.invoke({"@type": "sendChatAction", "chat_id": chat_id, "action": {"@type": "chatActionCancel"}})
        except Exception as e:
            c.logger.warning(f"Gagal membatalkan status mengunggah melalui invoke: {e}")
