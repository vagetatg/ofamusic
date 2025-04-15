#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client as PyroClient
from pyrogram import errors
from pytdbot import Client, types

from src.modules.utils.cacher import chat_cache
from src.pytgcalls import call


class InactiveCallManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Kolkata", event_loop=self.bot.loop
        )

    async def _end_inactive_calls(self, chat_id: int, semaphore: asyncio.Semaphore):
        async with semaphore:
            vc_users = await call.vc_users(chat_id)
            if len(vc_users) > 1:
                self.bot.logger.debug(
                    f"Active users detected in chat {chat_id}. Skipping..."
                )
                return

            # Check if the call has been active for more than 20 seconds
            played_time = await call.played_time(chat_id)
            if played_time < 20:
                self.bot.logger.debug(
                    f"Call in chat {chat_id} has been active for less than 20 seconds. Skipping..."
                )
                return

            # Notify the chat and end the call
            reply = await self.bot.sendTextMessage(
                chat_id, "⚠️ No active listeners detected. ⏹️ Leaving voice chat..."
            )
            if isinstance(reply, types.Error):
                self.bot.logger.warning(f"Error sending message: {reply}")
            await call.end(chat_id)

    async def end_inactive_calls(self):
        active_chats = chat_cache.get_active_chats()
        self.bot.logger.debug(
            f"Found {len(active_chats)} active chats. Ending inactive calls..."
        )
        if not active_chats:
            return

        # Use a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(3)
        tasks = [
            self._end_inactive_calls(chat_id, semaphore) for chat_id in active_chats
        ]

        # Process tasks in batches of 3 with a 1-second delay between batches
        for i in range(0, len(tasks), 3):
            await asyncio.gather(*tasks[i : i + 3])
            await asyncio.sleep(1)

        self.bot.logger.debug("Inactive call checks completed.")

    async def leave_all(self):
        for client_name, call_instance in call.calls.items():
            ub: PyroClient = call_instance.mtproto_client
            chats_to_leave = []
            async for dialog in ub.get_dialogs():
                chat = getattr(dialog, "chat", None)
                if not chat:
                    continue
                if chat.id > 0:
                    self.bot.logger.debug(
                        f"[{client_name}] Skipping private chat: {chat.id}"
                    )
                    continue
                chats_to_leave.append(chat.id)
            self.bot.logger.debug(
                f"[{client_name}] Found {len(chats_to_leave)} chats to leave."
            )
            for chat_id in chats_to_leave:
                is_active = chat_cache.is_active(chat_id)
                if is_active:
                    continue
                try:
                    await ub.leave_chat(chat_id)
                    self.bot.logger.debug(f"[{client_name}] Left chat {chat_id}")
                    await asyncio.sleep(0.5)
                except errors.FloodWait as e:
                    wait_time = e.value
                    self.bot.logger.warning(
                        f"[{client_name}] FloodWait for {wait_time}s on chat {chat_id}"
                    )
                    if wait_time > 100:
                        self.bot.logger.warning(
                            f"[{client_name}] Skipping due to long wait time."
                        )
                        continue
                    await asyncio.sleep(wait_time)
                except errors.RPCError as e:
                    self.bot.logger.warning(
                        f"[{client_name}] Failed to leave chat {chat_id}: {e}"
                    )
                    continue
                except Exception as e:
                    self.bot.logger.error(
                        f"[{client_name}] Error leaving chat {chat_id}: {e}"
                    )
                    continue

            self.bot.logger.info(f"[{client_name}] Leaving all chats completed.")

    async def start_scheduler(self):
        # Schedule the job to run every 50 seconds
        self.scheduler.add_job(self.end_inactive_calls, "interval", seconds=50)
        # Run every day at 12:00 AM
        self.scheduler.add_job(self.leave_all, CronTrigger(hour=0, minute=0))
        self.scheduler.start()
        self.bot.logger.info("Scheduler started.")

    async def stop_scheduler(self):
        self.scheduler.shutdown()
        self.bot.logger.info("Scheduler stopped.")
