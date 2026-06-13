import glob
import json
import os
import subprocess
import time
from pathlib import Path

import requests
from duckduckgo_search import DDGS

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
INBOX_DIR = Path(os.getenv("TASK_INBOX_DIR", "/app/tasks/inbox"))
OUTBOX_DIR = Path(os.getenv("TASK_OUTBOX_DIR", "/app/tasks/outbox"))
ARCHIVE_DIR = Path(os.getenv("TASK_ARCHIVE_DIR", "/app/tasks/archive"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "3"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "180"))
MAX_AGENT_LOOPS = int(os.getenv("MAX_AGENT_LOOPS", "10"))
WORKSPACE_DIR = Path(os.getenv("TASK_WORKSPACE_DIR", "/app/tasks/workspace"))

SYSTEM_PROMPT = """You are an autonomous task agent with access to tools.

Available tools:
- web_search(query) — search the web for current information
- run_python(code) — execute Python code and get the output
- read_file(path) — read a file from the workspace
- write_file(path, content) — write content to a file in the workspace
- list_files() — list all files in the workspace

To use a tool, respond with EXACTLY this JSON format (nothing else):
{"tool": "tool_name", "args": {"arg1": "value1"}}

When you have enough information to answer the task, respond with:
{"tool": "finish", "args": {"answer": "your complete final answer here"}}

Think step by step. Use tools when you need current info, need to compute something, or need to read/write files.
"""


# ── Tools ──────────────────────────────────────────────────────────────────────

def tool_web_search(query: str) -> str:
    try:
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r.get('title', '')}**\n{r.get('body', '')}\nURL: {r.get('href', '')}\n")
        return "\n".join(lines)
    except Exception as exc:
        return f"Search failed: {exc}"


def tool_run_python(code: str) -> str:
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout or ""
        error = result.stderr or ""
        if error:
            return f"stdout:\n{output}\nstderr:\n{error}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: code execution timed out (15s limit)"
    except Exception as exc:
        return f"Error: {exc}"


def tool_read_file(path: str) -> str:
    try:
        target = WORKSPACE_DIR / Path(path).name
        return target.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error reading file: {exc}"


def tool_write_file(path: str, content: str) -> str:
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        target = WORKSPACE_DIR / Path(path).name
        target.write_text(content, encoding="utf-8")
        return f"Written to {target}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def tool_list_files() -> str:
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        files = list(WORKSPACE_DIR.iterdir())
        if not files:
            return "Workspace is empty."
        return "\n".join(f.name for f in files)
    except Exception as exc:
        return f"Error listing files: {exc}"


TOOLS = {
    "web_search": lambda args: tool_web_search(args["query"]),
    "run_python": lambda args: tool_run_python(args["code"]),
    "read_file": lambda args: tool_read_file(args["path"]),
    "write_file": lambda args: tool_write_file(args["path"], args["content"]),
    "list_files": lambda args: tool_list_files(),
}


# ── LLM call ───────────────────────────────────────────────────────────────────

def chat(messages: list) -> str:
    payload = {"model": OLLAMA_MODEL, "stream": False, "messages": messages}
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "").strip()


# ── Agent loop ─────────────────────────────────────────────────────────────────

def ensure_dirs() -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def run_agent(task_text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_text},
    ]
    steps_log = [f"## Task\n{task_text}\n\n## Agent Steps\n"]

    for loop in range(1, MAX_AGENT_LOOPS + 1):
        print(f"  [loop {loop}] calling LLM...")
        raw = chat(messages)

        # Strip markdown code fences if the model wraps JSON in them
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            action = json.loads(clean)
        except json.JSONDecodeError:
            # LLM returned plain text — treat as final answer
            steps_log.append(f"### Step {loop}\nLLM returned plain text (no tool call).\n\n**Answer:**\n{raw}\n")
            return "".join(steps_log)

        tool_name = action.get("tool", "")
        args = action.get("args", {})

        if tool_name == "finish":
            answer = args.get("answer", raw)
            steps_log.append(f"### Step {loop}\n**Finished.**\n\n## Final Answer\n{answer}\n")
            return "".join(steps_log)

        if tool_name not in TOOLS:
            tool_result = f"Unknown tool: {tool_name}"
        else:
            print(f"  [loop {loop}] running tool: {tool_name}({args})")
            steps_log.append(f"### Step {loop}\n**Tool:** `{tool_name}`\n**Args:** `{json.dumps(args)}`\n")
            try:
                tool_result = TOOLS[tool_name](args)
            except Exception as exc:
                tool_result = f"Tool error: {exc}"
            steps_log.append(f"**Result:**\n```\n{tool_result[:2000]}\n```\n")
            print(f"  [loop {loop}] tool result: {tool_result[:200]}")

        # Feed tool result back into conversation
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": f"Tool result for {tool_name}:\n{tool_result}"})

    steps_log.append(f"\n## Final Answer\nReached max loops ({MAX_AGENT_LOOPS}). Last LLM response:\n{raw}\n")
    return "".join(steps_log)


# ── File watcher ───────────────────────────────────────────────────────────────

def process_task_file(task_file: Path) -> None:
    task_text = task_file.read_text(encoding="utf-8").strip()
    if not task_text:
        task_file.rename(ARCHIVE_DIR / f"{task_file.stem}.empty")
        print(f"Skipped empty task: {task_file.name}")
        return

    print(f"Processing task: {task_file.name}")

    try:
        result = run_agent(task_text)
        output_path = OUTBOX_DIR / f"{task_file.stem}.result.md"
        output_path.write_text(result + "\n", encoding="utf-8")

        task_file.rename(ARCHIVE_DIR / f"{task_file.stem}.done.txt")
        print(f"Done: {task_file.name} -> {output_path.name}")

    except Exception as exc:
        error_path = OUTBOX_DIR / f"{task_file.stem}.error.txt"
        error_path.write_text(f"Task failed: {exc}\n", encoding="utf-8")
        task_file.rename(ARCHIVE_DIR / f"{task_file.stem}.failed.txt")
        print(f"Failed: {task_file.name} ({exc})")


def run() -> None:
    ensure_dirs()
    print(f"Agent started | model: {OLLAMA_MODEL} | max loops: {MAX_AGENT_LOOPS}")
    print(f"Watching inbox: {INBOX_DIR}")

    while True:
        for raw_path in sorted(glob.glob(str(INBOX_DIR / "*.txt"))):
            process_task_file(Path(raw_path))
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
