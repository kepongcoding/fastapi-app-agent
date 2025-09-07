import json
import requests
import logging
import time
from pathlib import Path
from typing import Any, Dict

# ---------------- Logging Setup ---------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("sender")

# ---------------- Config ---------------- #
API_ENDPOINT = "http://127.0.0.1:4001/coliving-ai-os/api/raw-user-message/"
API_KEY = "supersecretapikey123"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY,
}

# ---------------- Sender Function ---------------- #
def send_messages_from_json(file_path: str, user_limit: int = 5, msg_limit: int = 10):
    """
    Reads messages from a JSON file and sends them to the API endpoint.
    
    Args:
        file_path: Path to the JSON file containing chat history.
        user_limit: Max number of users to process.
        msg_limit: Max number of messages to send per user.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"❌ JSON file not found: {file_path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        try:
            data: list[Dict[str, Any]] = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON: {e}")
            return

    # Expecting a list at the root
    for idx, user_entry in enumerate(data):
        if idx >= user_limit:
            break

        user_ns = user_entry.get("user_ns", "unknown")
        chat_history = user_entry.get("chat_history", [])

        logger.info(f"➡️ Processing user_ns={user_ns}, total_messages={len(chat_history)}")

        for msg in chat_history[:msg_limit]:
            try:
                msg_to_send = dict(msg)  # copy
                send_At_ts = send_At_ts = int(time.time() * 1000)
                msg_to_send["send_At"] = send_At_ts

                print(f"payload:{msg_to_send}, type:{type(msg_to_send)}")

                # Measure round-trip time
                start = time.perf_counter()
                response = requests.post(API_ENDPOINT, headers=HEADERS, json=msg_to_send)
                end = time.perf_counter()

                round_trip_ms = (end - start) * 1000
                server_latency_raw = response.headers.get("X-Process-Time-ms")
                try:
                    server_latency = float(server_latency_raw) if server_latency_raw else None
                except ValueError:
                    server_latency = None

                if response.status_code == 200:
                    logger.info(
                        f"✅ Sent message id={msg.get('id')} for user {user_ns} "
                        f"| Client RTT={round_trip_ms:.2f} ms "
                        f"| Server latency={server_latency:.2f} ms"
                        if server_latency is not None else
                        f"✅ Sent message id={msg.get('id')} for user {user_ns} "
                        f"| Client RTT={round_trip_ms:.2f} ms "
                        f"| Server latency=N/A"
                    )
                else:
                    logger.error(
                        f"❌ Failed to send message id={msg.get('id')} for user {user_ns} "
                        f"| Status={response.status_code}, Response={response.text} "
                        f"| Client RTT={round_trip_ms:.2f} ms "
                        f"| Server latency={server_latency:.2f} ms"
                        if server_latency is not None else
                        f"❌ Failed to send message id={msg.get('id')} for user {user_ns} "
                        f"| Status={response.status_code}, Response={response.text} "
                        f"| Client RTT={round_trip_ms:.2f} ms "
                        f"| Server latency=N/A"
                    )
            except Exception as e:
                logger.exception(f"💥 Error sending message id={msg.get('id')}: {e}")
        time.sleep(2)

# ---------------- Main ---------------- #
if __name__ == "__main__":
    file = r"C:\Users\User\TARUMT\project\Belive CoLiving\chat history\chat_history_2.json"
    send_messages_from_json(file, user_limit=1, msg_limit=1)