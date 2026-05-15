import glob
import os
import time
from pathlib import Path

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
INBOX_DIR = Path(os.getenv("TASK_INBOX_DIR", "/app/tasks/inbox"))
OUTBOX_DIR = Path(os.getenv("TASK_OUTBOX_DIR", "/app/tasks/outbox"))
ARCHIVE_DIR = Path(os.getenv("TASK_ARCHIVE_DIR", "/app/tasks/archive"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "3"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "180"))

SYSTEM_PROMPT = (
    "You are an autonomous task agent. "
    "Take the given user task and produce: "
    "1) a short plan, 2) execution notes, and 3) final answer. "
    "Be practical and concise."
)


def ensure_dirs() -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def ask_ollama(task_text: str) -> str:
    chat_payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task_text},
        ],
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=chat_payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code == 404:
        generate_payload = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "prompt": f"{SYSTEM_PROMPT}\n\nUser task:\n{task_text}",
        }
        fallback_response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=generate_payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        fallback_response.raise_for_status()
        fallback_body = fallback_response.json()
        return fallback_body.get("response", "")

    response.raise_for_status()
    body = response.json()
    return body.get("message", {}).get("content", "")


def process_task_file(task_file: Path) -> None:
    task_text = task_file.read_text(encoding="utf-8").strip()
    if not task_text:
        task_file.rename(ARCHIVE_DIR / f"{task_file.stem}.empty")
        print(f"Skipped empty task: {task_file.name}")
        return

    print(f"Processing task file: {task_file.name}")

    try:
        result = ask_ollama(task_text)
        output_path = OUTBOX_DIR / f"{task_file.stem}.result.md"
        output_path.write_text(result + "\n", encoding="utf-8")

        done_path = ARCHIVE_DIR / f"{task_file.stem}.done.txt"
        task_file.rename(done_path)

        print(f"Done: {task_file.name} -> {output_path.name}")
    except Exception as exc:
        error_path = OUTBOX_DIR / f"{task_file.stem}.error.txt"
        error_path.write_text(f"Task failed: {exc}\n", encoding="utf-8")

        failed_path = ARCHIVE_DIR / f"{task_file.stem}.failed.txt"
        task_file.rename(failed_path)

        print(f"Failed: {task_file.name} ({exc})")


def run() -> None:
    ensure_dirs()
    print(f"Agent started with model: {OLLAMA_MODEL}")
    print(f"Watching inbox: {INBOX_DIR}")

    while True:
        task_paths = sorted(glob.glob(str(INBOX_DIR / "*.txt")))
        if task_paths:
            for raw_path in task_paths:
                process_task_file(Path(raw_path))
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
