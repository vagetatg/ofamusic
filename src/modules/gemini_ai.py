#  Copyright (c) 2025 ubaynet
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import json

from pytdbot import Client, types

from src.config import OWNER_ID
from src.helpers import get_string
from src.modules.utils import Filter
from src.modules.utils.play_helpers import extract_argument

@Client.on_message(filters=Filter.command("ask"))
async def ask_gemini(c: Client, message: types.Message) -> None:
    """
    Handle the /ask command to interact with Gemini AI.
    """
    chat_id = message.chat_id
    lang = await c.db.get_lang(chat_id)

    # Extract the user's question from the command arguments
    question = extract_argument(message.text)
    if not question:
        await message.reply_text(get_string("ask_usage", lang))
        return

    # Send a typing indicator while processing
    await c.sendChatAction(chat_id, types.ChatActionTyping())

    # Prepare chat history for Gemini API call
    chat_history = []
    chat_history.append({"role": "user", "parts": [{"text": question}]})
    payload = {"contents": chat_history}

    # Gemini API endpoint (assuming gemini-2.0-flash by default)
    api_key = "" # Leave as is, Canvas will inject the key
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    try:
        # Make the API call
        response = await asyncio.to_thread(
            lambda: __import__('requests').post(
                api_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload)
            ).json()
        )

        # Check for candidates and content
        if response.get("candidates") and response["candidates"][0].get("content") and \
           response["candidates"][0]["content"].get("parts") and \
           response["candidates"][0]["content"]["parts"][0].get("text"):
            
            gemini_response = response["candidates"][0]["content"]["parts"][0]["text"]
            await message.reply_text(f"<b>{get_string('answer', lang)}:</b>\n{gemini_response}")
        else:
            await message.reply_text(get_string("gemini_no_response", lang))

    except Exception as e:
        await message.reply_text(f"{get_string('gemini_error', lang)}: {e}")
        c.logger.error(f"Error calling Gemini API: {e}")

