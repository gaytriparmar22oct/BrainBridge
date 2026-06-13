# BrainBridge — Local Agentic AI Stack

A fully local AI stack that runs on Docker. It includes:

- **Ollama** — local LLM server (runs models like `qwen2.5-coder:7b`, `llama3.1:8b`, etc.)
- **Open WebUI** — a ChatGPT-style browser interface at `http://localhost:3000`
- **Task Agent** — an autonomous Python agent that processes `.txt` task files, uses tools (web search, code execution, file I/O), and writes results back to disk

No cloud APIs. No GitHub Copilot. Everything runs locally on your machine.

---

## Architecture

```
You ──► http://localhost:3000  (Open WebUI)  ──┐
                                               ├──► Ollama  ──► LLM model
tasks/inbox/*.txt ──► task_agent ──────────────┘
                          │
                          ├── web_search()      ← DuckDuckGo (no API key)
                          ├── run_python()      ← executes code, returns output
                          ├── read_file()       ← reads from tasks/workspace/
                          ├── write_file()      ← writes to tasks/workspace/
                          │
                          ▼
                   tasks/outbox/*.result.md     ← answer + agent step log
                   tasks/archive/*.done.txt     ← original task archived
                   tasks/workspace/             ← files created by the agent
```

---

## How the Agent Works

The agent uses a **tool-calling loop** — instead of a single LLM call, it:

1. Reads the task from `tasks/inbox/*.txt`
2. Asks the LLM what to do next
3. LLM picks a tool (web search, run code, read/write file, or finish)
4. Agent runs the tool and feeds the result back to the LLM
5. Loop repeats (up to `MAX_AGENT_LOOPS`) until LLM returns a final answer
6. Full step-by-step log + final answer written to `tasks/outbox/*.result.md`

### Available Tools

| Tool | What it does |
|---|---|
| `web_search(query)` | Searches DuckDuckGo, returns top 5 results |
| `run_python(code)` | Executes Python code, returns stdout/stderr |
| `read_file(path)` | Reads a file from `tasks/workspace/` |
| `write_file(path, content)` | Writes a file to `tasks/workspace/` |
| `list_files()` | Lists all files in `tasks/workspace/` |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS, or Linux)
- Docker Compose v2 (bundled with Docker Desktop)
- ~15 GB free disk space (Docker images + LLM model weights)
- 8 GB+ RAM recommended (16 GB for the 7B/8B models)

> On Windows, if `docker` is not recognized in PowerShell, add
> `C:\Program Files\Docker\Docker\resources\bin` to your PATH or restart your terminal after installing Docker Desktop.

---

## Quick Start

1. Clone the repo:
   ```bash
   git clone https://github.com/gaytriparmar22oct/BrainBridge.git
   cd BrainBridge
   ```

2. Start all services:
   ```bash
   docker compose up --build -d
   ```

3. The default model defined in `.env` will be pulled automatically by the `model_init` container.
   This can take several minutes on the first run (model is ~5 GB).

4. Open the ChatGPT-style UI at **http://localhost:3000**.

5. Use the autonomous task agent:
   - Drop a plain text task into `tasks/inbox/`, e.g. `tasks/inbox/002.txt`
   - Wait a few seconds for the agent to process it
   - Read the answer + step log at `tasks/outbox/002.result.md`
   - The original task is moved to `tasks/archive/`

### Example Tasks

**Web search:**
```
tasks/inbox/002.txt
---
What is the latest stable release of Kubernetes? Search the web and summarise the key changes.
```

**Code execution:**
```
tasks/inbox/003.txt
---
Write a Python script that generates the first 20 Fibonacci numbers, run it, and save the output to fibonacci.txt
```

**Multi-step research:**
```
tasks/inbox/004.txt
---
Search for the top 3 Python web frameworks in 2025, compare them, and write a summary to frameworks.md
```

---

## Configuration

Edit the `.env` file in the project root:

```env
OLLAMA_MODEL=qwen2.5-coder:7b
POLL_INTERVAL_SECONDS=3
REQUEST_TIMEOUT_SECONDS=180
MAX_AGENT_LOOPS=10
```

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Ollama model tag to pull and use |
| `POLL_INTERVAL_SECONDS` | `3` | How often the agent checks `tasks/inbox/` |
| `REQUEST_TIMEOUT_SECONDS` | `180` | Max time to wait for the LLM per call |
| `MAX_AGENT_LOOPS` | `10` | Max tool-calling iterations per task |

Popular model choices:
- `qwen2.5-coder:7b` — best for coding tasks (~4.7 GB)
- `qwen2.5:7b` — strong general-purpose (~4.7 GB)
- `llama3.1:8b` — Meta's Llama 3.1 (~4.9 GB)
- `llama3.2:3b` — smaller/faster, lower RAM (~2 GB)

Apply changes:
```bash
docker compose down
docker compose up --build -d
```

---

## Managing Models

```bash
# List installed models
docker compose exec ollama ollama list

# Pull a new model
docker compose exec ollama ollama pull llama3.2:3b

# Remove a model (frees disk space)
docker compose exec ollama ollama rm qwen2.5:7b
```

---

## Useful Commands

| Command | Purpose |
|---|---|
| `docker compose up --build -d` | Start everything in the background |
| `docker compose ps` | See running services and health |
| `docker compose logs -f task_agent` | Tail agent logs (see tool calls live) |
| `docker compose logs -f ollama` | Tail Ollama logs |
| `docker compose restart open_webui` | Restart the UI |
| `docker compose down` | Stop all services |

---

## Architecture

```
You ──► http://localhost:3000  (Open WebUI)  ──┐
                                               ├──► Ollama  ──► LLM model
tasks/inbox/*.txt ──► task_agent ──────────────┘
                          │
                          ▼
                   tasks/outbox/*.result.md
                   tasks/archive/*.done.txt
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS, or Linux)
- Docker Compose v2 (bundled with Docker Desktop)
- ~15 GB free disk space (Docker images + LLM model weights)
- 8 GB+ RAM recommended (16 GB for the 7B/8B models)

> On Windows, if `docker` is not recognized in PowerShell, add
> `C:\Program Files\Docker\Docker\resources\bin` to your PATH or restart your terminal after installing Docker Desktop.

---

## Quick start

1. Clone the repo:
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. Start all services:
   ```bash
   docker compose up --build -d
   ```

3. The default model defined in `.env` will be pulled automatically by the `model_init` container.
   This can take several minutes on the first run (model is ~5 GB).

4. Open the ChatGPT-style UI at **http://localhost:3000**.
   Pick your model from the dropdown and start chatting.

5. (Optional) Use the autonomous task agent:
   - Drop a plain text task into `tasks/inbox/`, e.g. `tasks/inbox/002.txt`
   - Wait a few seconds
   - Read the answer at `tasks/outbox/002.result.md`
   - The original task is moved to `tasks/archive/`

---

## Configuration

Edit the `.env` file in the project root:

```env
OLLAMA_MODEL=qwen2.5:7b
POLL_INTERVAL_SECONDS=3
REQUEST_TIMEOUT_SECONDS=180
```

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model tag to pull and use |
| `POLL_INTERVAL_SECONDS` | `3` | How often the agent checks `tasks/inbox/` |
| `REQUEST_TIMEOUT_SECONDS` | `180` | Max time to wait for the LLM to respond |

Popular model choices:
- `qwen2.5:7b` — strong general-purpose (~4.7 GB)
- `qwen2.5-coder:7b` — best for coding tasks (~4.7 GB)
- `llama3.1:8b` — Meta's Llama 3.1 (~4.9 GB)
- `llama3.2:3b` — smaller/faster, lower RAM (~2 GB)

Apply changes:
```bash
docker compose down
docker compose up --build -d
```

---

## Managing models

```bash
# List installed models
docker compose exec ollama ollama list

# Pull a new model
docker compose exec ollama ollama pull qwen2.5-coder:7b

# Remove a model (frees disk space)
docker compose exec ollama ollama rm llama3.1:8b
```

---

## Useful commands

| Command | Purpose |
|---|---|
| `docker compose up --build -d` | Start everything in the background |
| `docker compose ps` | See running services |
| `docker compose logs -f task_agent` | Tail agent logs |
| `docker compose logs -f ollama` | Tail Ollama logs |
| `docker compose restart open_webui` | Restart the UI |
| `docker compose down` | Stop all services |
| `docker compose down -v` | Stop and delete all volumes (removes models!) |
| `docker system df` | Show Docker disk usage |
| `docker system prune -a` | Reclaim unused images/layers |

---

## Project layout

```
.
├── agent/
│   ├── Dockerfile          # Builds the Python task agent image
│   ├── requirements.txt    # Agent Python dependencies
│   └── agent.py            # Polls tasks/inbox and calls Ollama
├── tasks/
│   ├── inbox/              # Drop *.txt tasks here
│   ├── outbox/             # Results written here as *.result.md
│   └── archive/            # Processed task files
├── .env                    # Model + tuning config
├── docker-compose.yml      # Defines ollama, model_init, open_webui, task_agent
└── README.md
```

---

## Troubleshooting

**Open WebUI shows no models**
The model is still downloading. Watch progress:
```bash
docker compose logs -f model_init
```
Then refresh `http://localhost:3000`.

**`docker: command not found` on Windows PowerShell**
Either reopen the terminal after installing Docker Desktop, or add Docker to PATH:
```powershell
$env:Path += ";C:\Program Files\Docker\Docker\resources\bin"
```

**Agent error: `404 Not Found for /api/chat`**
The model isn't downloaded yet. Run:
```bash
docker compose exec ollama ollama pull <model-from-.env>
```

**Out of memory / slow responses**
Switch to a smaller model in `.env`, e.g. `OLLAMA_MODEL=llama3.2:3b`.

---

## Disk space

Approximate footprint:

| Item | Size |
|---|---|
| Ollama image | ~1.5 GB |
| Open WebUI image | ~3 GB |
| Task agent image | ~200 MB |
| Each 7B–8B model | ~5 GB |
| **Typical total** | **~10–15 GB** |

To free everything:
```bash
docker compose down -v
docker system prune -a
```

---

## License

MIT — feel free to use, modify, and share.
