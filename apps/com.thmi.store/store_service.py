import logging

from mpos import Service, TaskManager, WifiService

logger = logging.getLogger(__name__)


class StoreService(Service):

    def onStart(self, intent):
        TaskManager.create_task(self._run())

    async def _run(self):
        try:
            for _ in range(12):                      # wait up to ~1 min for Wi-Fi
                if WifiService.is_connected():
                    break
                await TaskManager.sleep(5)
            else:
                return
            import store_core
            done = await store_core.maintain()
            if done:
                logger.info("auto-updated: %s", done)
        except Exception as e:
            logger.warning("auto update skipped: %s", e)
