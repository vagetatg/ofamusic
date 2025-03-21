from pytdbot import Client, types

import config
from src.database import db
from src.modules.jobs import InactiveCallManager
from src.pytgcalls import call, start_clients


class Telegram(Client):
    def __init__(self) -> None:
        super().__init__(
            token=config.TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            default_parse_mode="html",
            td_verbosity=2,
            td_log=types.LogStreamEmpty(),
            plugins=types.plugins.Plugins(folder="src/modules"),
            files_directory="",
            database_encryption_key="",
            options={"ignore_background_updates": True},
        )
        self.call_manager = InactiveCallManager(self)
        self.db = db

    async def start(self, *args, **kwargs) -> None:
        await super().start()
        await self.db.ping()
        await start_clients()
        await call.add_bot(self)
        await call.register_decorators()
        await self.call_manager.start_scheduler()
        self.logger.info("✅ Bot started successfully.")

    async def stop(self, *args, **kwargs) -> None:
        await super().stop()
        # await self.call_manager.stop_scheduler()
        await self.db.close()


client = Telegram()
__version__ = "1.0.0"
