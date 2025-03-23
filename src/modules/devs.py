import asyncio
import inspect
import io
import os
import platform
import re
import socket
import sys
import time
import traceback
import uuid
from html import escape
from sys import version as pyver
from typing import Any, List, Optional, Tuple

import psutil
import pyrogram
from meval import meval
from ntgcalls import __version__ as ntgver
from pyrogram import Client, filters, types, errors
from pyrogram import __version__ as pyrover
from pyrogram.enums import ChatType
from pytgcalls.__version__ import __version__ as pytgver

from config import OWNER_ID
from src import db
from src.logger import LOGGER
from src.modules.utils.play_helpers import del_msg
from src.pytgcalls import call


def format_exception(
        exp: BaseException, tb: Optional[List[traceback.FrameSummary]] = None
) -> str:
    """Formats an exception traceback as a string, similar to the Python interpreter."""

    if tb is None:
        tb = traceback.extract_tb(exp.__traceback__)

    # Replace absolute paths with relative paths
    cwd = os.getcwd()
    for frame in tb:
        if cwd in frame.filename:
            frame.filename = os.path.relpath(frame.filename)

    stack = "".join(traceback.format_list(tb))
    msg = str(exp)
    if msg:
        msg = f": {msg}"

    return f"Traceback (most recent call last):\n{stack}{type(exp).__name__}{msg}"


@Client.on_message(filters.command("eval") & filters.user(OWNER_ID))
async def exec_eval(c: Client, m: pyrogram.types.Message):
    text = m.text.split(None, 1)
    if len(text) <= 1:
        await m.reply_text("🛑 Usage: /eval code")
        return

    code = text[1]
    out_buf = io.StringIO()

    async def _eval() -> Tuple[str, Optional[str]]:
        # Message sending helper for convenience
        async def send(*args: Any, **kwargs: Any) -> pyrogram.types.Message:
            return await m.reply(*args, **kwargs)

        def _print(*args: Any, **kwargs: Any) -> None:
            if "file" not in kwargs:
                kwargs["file"] = out_buf
                return print(*args, **kwargs)

        eval_vars = {
            "loop": c.loop,
            "client": c,
            "stdout": out_buf,
            "c": c,
            "m": m,
            "msg": m,
            "message": m,
            "raw": pyrogram.raw,
            "send": send,
            "print": _print,
            "inspect": inspect,
            "os": os,
            "re": re,
            "sys": sys,
            "traceback": traceback,
            "pyrogram": pyrogram,
            "uuid": uuid,
            "io": io,
            "tgcall": call,
        }

        try:
            return "", await meval(code, globals(), **eval_vars)
        except Exception as e:
            first_snip_idx = -1
            tb = traceback.extract_tb(e.__traceback__)
            for i, frame in enumerate(tb):
                if frame.filename == "<string>" or frame.filename.endswith("ast.py"):
                    first_snip_idx = i
                    break

            # Re-raise exception if it wasn't caused by the snippet
            if first_snip_idx == -1:
                raise e
            # Return formatted stripped traceback
            stripped_tb = tb[first_snip_idx:]
            formatted_tb = format_exception(e, tb=stripped_tb)
            return "⚠️ Error:\n\n", formatted_tb

    prefix, result = await _eval()

    if not out_buf.getvalue() or result is not None:
        print(result, file=out_buf)

    out = out_buf.getvalue()
    if out.endswith("\n"):
        out = out[:-1]

    result = f"""{prefix}<b>In:</b>
<pre language="python">{escape(code)}</pre>
<b>ᴏᴜᴛ:</b>
<pre language="python">{escape(out)}</pre>"""

    if len(result) > 4096:
        with io.BytesIO(str.encode(out)) as out_file:
            out_file.name = str(uuid.uuid4()).split("-")[0].lower() + ".txt"
            caption = f"""{prefix}<b>ᴇᴠᴀʟ:</b>
<pre language="python">{escape(code)}</pre>
"""
            await m.reply_document(document=out_file, caption=caption)
        return None

    await m.reply_text(result)


REQUEST = 10
semaphore = asyncio.Semaphore(REQUEST)


@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(_, message: types.Message):
    all_users: list[int] = await db.get_all_users()
    all_chats: list[int] = await db.get_all_chats()
    reply = message.reply_to_message

    if not reply:
        await message.reply_text("Reply to a message to broadcast it.")
        return

    if not all_users and not all_chats:
        await message.reply_text("No users or chats to broadcast to.")
        return

    async def broadcast_target(target_list, reply_message, _semaphore):
        sent, failed = 0, 0
        for target_id in target_list:
            try:
                async with _semaphore:
                    await reply_message.copy(target_id)
                sent += 1
            except errors.FloodWait as e:
                LOGGER.warning(f"FloodWait detected for {target_id}, waiting {e.value}s")
                await asyncio.sleep(e.value + 1)
                async with _semaphore:
                    await reply_message.copy(target_id)
                sent += 1
            except errors.ChannelInvalid:
                failed += 1
                await db.remove_chat(target_id)
            except (errors.UserDeactivated, errors.InputUserDeactivated):
                failed += 1
                await db.remove_user(target_id)
            except errors.UserIsBlocked:
                failed += 1
                await db.remove_user(target_id)
            except errors.TopicIdInvalid:
                failed += 1
            except errors.PeerIdInvalid:
                failed += 1
            except Exception as e:
                LOGGER.error(f"Failed to send to {target_id}: {e}")
                failed += 1
        return sent, failed

    user_sent, user_failed = await broadcast_target(all_users, reply, semaphore)
    chat_sent, chat_failed = await broadcast_target(all_chats, reply, semaphore)

    total_sent = user_sent + chat_sent
    total_failed = user_failed + chat_failed

    await message.reply_text(
        f"Broadcast completed:\n"
        f"- Sent: {total_sent} (Users: {user_sent}, Chats: {chat_sent})\n"
        f"- Failed: {total_failed} (Users: {user_failed}, Chats: {chat_failed})"
    )


@Client.on_message(filters.command("leave") & filters.user(OWNER_ID))
async def leave_cmd(client, message: types.Message):
    try:
        await message.delete()
    except Exception as e:
        LOGGER.warning(f"Error deleting message: {e}")

    args = message.text.split(" ")
    chat_id = message.chat.id if len(args) < 2 else args[1]
    try:
        await client.leave_chat(chat_id)
    except Exception as e:
        await message.reply_text(f"Error leaving the chat: {e}")
    return


@Client.on_message(filters.command("ping") & filters.user(OWNER_ID))
async def ping_cmd(_, message: types.Message):
    chat_id = 1 if message.chat.type == ChatType.PRIVATE else message.chat.id
    reply = await message.reply_text("🔎 Pinging...", disable_notification=True, disable_web_page_preview=True)
    try:
        ping, cpu_usage = await call.stats_call(chat_id=chat_id)
        memory_info = psutil.virtual_memory()
        memory_usage = f"{memory_info.percent}%"
        uptime = int(time.time() - psutil.boot_time())
        load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

        text = (
            f"<b>» Pong!</b>\n\n"
            f"<b>» NTgCalls Ping:</b> {ping} ms\n"
            f"<b>» CPU Usage:</b> {cpu_usage:.3f}%\n"
            f"<b>» Memory Usage:</b> {memory_usage}\n"
            f"<b>» System Uptime:</b> {uptime // 3600}h {uptime % 3600 // 60}m {uptime % 60}s\n"
            f"<b>» Load Average:</b> {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        )
        await reply.edit_text(text)
    except Exception as e:
        LOGGER.warning(f"Error sending ping: {e}")
        str_e = str(e).replace("Telegram says", "\nERROR")
        await reply.edit_text("An error occurred while sending the ping.\n\n" + str_e)

    return


@Client.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def sys_stats(client, message: types.Message):
    await del_msg(message)
    if message.chat.type != ChatType.PRIVATE:
        return await message.reply_text("This command can only be used in PM.")

    sysroot = await message.reply_text(
        f"ɢᴇᴛᴛɪɴɢ {client.me.mention} sʏsᴛᴇᴍ sᴛᴀᴛs, ɪᴛ'ʟʟ ᴛᴀᴋᴇ ᴀ ᴡʜɪʟᴇ..."
    )

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(socket.gethostname())
    architecture = platform.machine()
    mac_address = ":".join(re.findall("..", "%012x" % uuid.getnode()))
    sp = platform.system()
    ram = f"{str(round(psutil.virtual_memory().total / 1024.0 ** 3))} ɢʙ"
    p_core = psutil.cpu_count(logical=False)
    t_core = psutil.cpu_count(logical=True)

    try:
        cpu_freq = psutil.cpu_freq().current
        if cpu_freq >= 1000:
            cpu_freq = f"{round(cpu_freq / 1000, 2)}ɢʜᴢ"
        else:
            cpu_freq = f"{round(cpu_freq, 2)}ᴍʜᴢ"
    except Exception as e:
        LOGGER.warning(f"Error getting CPU frequency: {e}")
        cpu_freq = "ғᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ"

    hdd = psutil.disk_usage("/")
    total = hdd.total / (1024.0 ** 3)
    used = hdd.used / (1024.0 ** 3)
    free = hdd.free / (1024.0 ** 3)
    platform_release = platform.release()
    platform_version = platform.version()
    chats = len(await db.get_all_chats())
    users = len(await db.get_all_users())

    await sysroot.edit_text(
        f"""
<b><u>{client.me.mention} sʏsᴛᴇᴍ sᴛᴀᴛs</u></b>

<b>Chats:</b> {chats}
<b>Users:</b> {users}

<b>Python:</b> {pyver.split()[0]}
<b>Pyrogram:</b> {pyrover}
<b>Py-TgCalls:</b> {pytgver}
<b>NTGCalls:</b> {ntgver}

<b>IP:</b> {ip_address}
<b>MAC:</b> {mac_address}
<b>Hostname:</b> {hostname}
<b>Platform:</b> {sp}
<b>Architecture:</b> {architecture}
<b>Platform Release:</b> {platform_release}
<b>Platform Version:</b> {platform_version}

<b><u>Storage</u></b>
<b>Available:</b> {total:.2f} GiB
<b>Used:</b> {used:.2f} GiB
<b>Free:</b> {free:.2f} GiB

<b>RAM:</b> {ram}
<b>Physical Cores:</b> {p_core}
<b>Total Cores:</b> {t_core}
<b>CPU Frequency:</b> {cpu_freq}""",
    )
