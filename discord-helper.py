import asyncio
import json
import logging
import ssl
import pathlib
import websockets
from pypresence import AioPresence

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
MAX_RETRIES = 10
RETRY_DELAY = 3
HERE = pathlib.Path(__file__).parent
CERT_FILE = HERE / "localhost.pem"
KEY_FILE  = HERE / "localhost-key.pem"
class DiscordHelper:
    def __init__(self):
        self.rpc = None
        self.client_id = None
        self.connected = False

    async def connect_rpc(self, client_id):
        if self.connected and self.client_id == client_id:
            return

        if self.rpc:
            try:
                await self.rpc.close()
            except:
                pass

        self.client_id = client_id
        self.connected = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logging.info(f"Connecting to Discord RPC (attempt {attempt}/{MAX_RETRIES})...")
                self.rpc = AioPresence(client_id)
                await self.rpc.connect()
                self.connected = True
                logging.info(f"Connected to Discord RPC with Client ID: {client_id}")
                return
            except Exception as e:
                logging.warning(f"Attempt {attempt} failed: {e}")
                if self.rpc:
                    try:
                        await self.rpc.close()
                    except:
                        pass
                    self.rpc = None

                if attempt < MAX_RETRIES:
                    logging.info(f"Retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logging.error("All connection attempts failed. Is your Discord desktop app running? Try restarting it.")

    async def handle_client(self, websocket):
        logging.info("Website connected to helper!")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action")

                    if action == "init":
                        client_id = data.get("client_id")
                        if client_id:
                            await self.connect_rpc(client_id)

                    elif action == "set_activity":
                        if not self.connected:
                            logging.warning("Received set_activity but RPC is not connected. Retrying connect...")
                            if self.client_id:
                                await self.connect_rpc(self.client_id)
                            if not self.connected:
                                continue

                        activity = data.get("activity", {})
                        details = activity.get("details")
                        state = activity.get("state")
                        start_time = activity.get("timestamps", {}).get("start")

                        if start_time:
                            start_time = int(start_time / 1000)

                        try:
                            await self.rpc.update(
                                details=details,
                                state=state,
                                start=start_time
                            )
                            logging.info(f"Updated presence: {details} | {state}")
                        except Exception as e:
                            logging.error(f"Failed to update presence: {e}")
                            self.connected = False

                    elif action == "clear_activity":
                        if self.connected:
                            try:
                                await self.rpc.clear()
                                logging.info("Cleared presence.")
                            except Exception as e:
                                logging.error(f"Failed to clear presence: {e}")

                except json.JSONDecodeError:
                    logging.error("Received invalid JSON")

        except websockets.exceptions.ConnectionClosed:
            logging.info("Website disconnected.")
            if self.connected:
                try:
                    await self.rpc.clear()
                    logging.info("Cleared presence due to disconnect.")
                except:
                    pass


async def main():
    if not CERT_FILE.exists() or not KEY_FILE.exists():
        logging.error(
            "SSL certificate not found!\n"
            "Run the certificate generator first:\n"
            "  python gen_cert.py\n"
            "(mkcert users: make sure you ran 'mkcert localhost' in this folder)"
        )
        return

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    helper = DiscordHelper()
    logging.info("starting secure local helper WebSocket server on wss://localhost:8080")
    logging.info("make sure your Discord DESKTOP app is running before playing anything.")
    logging.info(
        "IMPORTANT: if this is your first time, visit https://localhost:8080 in your browser\n"
        "           and click 'Advanced > proceed to localhost' to trust the self-signed cert."
    )

    async with websockets.serve(helper.handle_client, "localhost", 8080, ssl=ssl_ctx):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Exiting...")
