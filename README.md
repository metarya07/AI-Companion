# JARVIS — a local AI desktop assistant

JARVIS is a small, friendly command-line assistant that runs entirely on
your machine. It can tell the time, remember notes and preferences, track
tasks, report system stats, manage files, close runaway processes, launch
applications and websites, scaffold code projects, run scheduled jobs,
research topics and hold a conversation through a local or hosted AI
model, and (optionally) listen to your voice and read your screen.

It is intentionally easy to read and extend: every capability is a
self-contained **skill**, and adding a new one is a one-line change.

```text
You ─▶ Brain ─▶ Intent Router ─▶ Skill Manager ─▶ Skill ─▶ reply
                     ▲                  ▲
                     └──── Skill Registry (plugins) ────┘
```

## New in v0.9 — the agent expansion

Version 0.9 builds toward the multi-agent vision in
[`PROJECT_JARVIS.md`](PROJECT_JARVIS.md). Each "agent" is just a group of
skills sharing the same plugin architecture, so the system stayed simple
and fully tested while growing from 5 capabilities to 14.

- **Memory agent.** Notes (from v0.5) plus **preferences** (`set name
  Tony`, `get name`) and a persistent **conversation history** every turn
  is logged to (`history`).
- **Planning agent.** A task list with natural due dates (`task submit
  report due friday`), completion (`done 2`) and an `agenda` of what's
  overdue or due today.
- **Computer control.** Safe **file management** — list, find, move,
  copy, `organize` files into type folders, `clean` loose files into a
  dated folder, and `backup` a folder to a zip — plus **process control**
  (`close chrome`, `processes`). Nothing is ever deleted, and everything
  respects dry-run.
- **Automation agent.** Register recurring commands (`schedule clean
  ~/Downloads every sunday at 09:00`) that run when `jarvis --run-due` is
  invoked by cron or Task Scheduler.
- **Coding agent.** Scaffold a starter Python project or Java class
  (`scaffold python my_app`, `scaffold java Student`). Explaining and
  debugging code is handled by the AI assistant.
- **Research agent.** Briefings, comparisons and summaries (`research
  reinforcement learning`, `compare PostgreSQL vs MySQL`). This uses the
  AI model's own knowledge — it does not fetch live web pages yet — and
  says so plainly when the model isn't reachable.

Everything is offline-first and degrades gracefully: features that need a
model, a microphone, a screen or `psutil` explain how to enable
themselves instead of crashing.

## What's in this version

This rebuild fixes the launcher bug from the roadmap and folds in the
planned features (websites, voice, AI, vision) along with a number of
engineering improvements:

- **The app-launcher crash is fixed.** The old launcher walked
  `C:\Program Files` for an `.exe`, wandered into the ACL-locked
  `WindowsApps` folder, and threw `PermissionError: [WinError 5]`. The
  new launcher discovers apps the reliable way — Start Menu shortcuts on
  Windows, `.app` bundles on macOS, `.desktop` entries on Linux — and is
  fully **cross-platform**.
- **Skills are plugins.** A registry maps command words to skills, so the
  router and manager never need editing when you add a skill. Help text
  is generated from the registry and can't drift out of date.
- **Memory has a fixed home.** The SQLite file lives next to the project
  (or wherever `JARVIS_DB_PATH` points) instead of in the current working
  directory, so your notes can't silently fragment across folders.
- **System stats are instant.** CPU usage is sampled without the old
  one-second-per-call block.
- **It won't crash on exit.** `Ctrl-C` / `Ctrl-D` and empty input are
  handled cleanly.
- **Real tests.** A `pytest` suite with assertions (no print-scripts, and
  it never touches your real database).
- **Configuration via environment variables**, with secrets kept out of
  the source tree.

## Requirements

- Python 3.9 or newer
- [`psutil`](https://pypi.org/project/psutil/) — the only required
  dependency (used by the system-stats skill)

Everything else (voice, vision, the AI providers) is optional and
degrades gracefully when not installed.

## Install

```bash
# from the project folder
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py                       # interactive prompt
python main.py --once "status"       # run one command and quit
python main.py --voice               # voice mode (needs the voice extras)
python main.py --run-due             # run any scheduled commands now due
python main.py --version
```

A session looks like this:

```text
=== JARVIS v0.9.0 ===  (type 'help', or 'exit' to quit)
JARVIS > remember submit the lab report friday
Memory saved (#1).
JARVIS > status
CPU usage: 7.4%
RAM usage: 38.2% (6.1 / 16.0 GB)
Disk usage: 55.0% (275.0 / 500.0 GB)
Uptime: 3h 12m
JARVIS > open github.com
Opening https://github.com
JARVIS > exit
Goodbye.
```

## Commands

| Command | What it does |
| --- | --- |
| `help` | List every available command |
| `version` | Show the JARVIS version |
| `time` / `date` | Current time / today's date |
| `remember <text>` | Save a note |
| `recall` | List saved notes |
| `search <text>` | Find notes containing some text |
| `forget <id>` | Delete a note by id |
| `cpu` / `ram` / `disk` | Individual resource readings |
| `battery` / `uptime` | Battery level / how long the machine's been on |
| `status` | A full system snapshot |
| `open <app>` | Launch an installed application (`open chrome`) |
| `open <site>` | Open a website (`open google`, `open youtube.com`) |
| `website <name>` | Force-open something as a website |
| `ask <question>` | Ask the AI assistant |
| *(anything else)* | Unrecognised input is sent to the AI assistant |
| `exit` / `quit` / `bye` | Leave |

### Agent commands (v0.9)

| Command | What it does |
| --- | --- |
| `set <key> <value>` | Save a preference (`set name Tony`) |
| `get <key>` / `prefs` | Read one / list all preferences |
| `unset <key>` | Remove a preference |
| `task <text> [due <when>]` | Add a task (`due friday`, `due 2026-06-20`, `due tomorrow`) |
| `tasks` / `tasks all` | List pending / all tasks |
| `done <id>` | Mark a task complete |
| `agenda` | Show overdue and due-today tasks |
| `history [n]` / `history clear` | Show / clear the conversation log |
| `ls [path]` | List a folder |
| `find <pattern> [in <path>]` | Find files (`find *.pdf in ~/Documents`) |
| `move` / `copy <src> <dst>` | Move or copy a file/folder |
| `organize [path]` | Sort files into type folders (images, documents…) |
| `clean [path]` | Sweep loose files into a dated folder (nothing deleted) |
| `backup <path>` | Zip a folder next to itself |
| `close <app>` | Close processes matching a name |
| `processes` | Top processes by memory use |
| `schedule <command> every <when>` | Register a recurring command |
| `schedules` / `unschedule <id>` | List / remove schedules |
| `scaffold python <name>` | Create a starter Python project |
| `scaffold java <ClassName>` | Create a starter Java class |
| `research <topic>` | An AI briefing on a topic |
| `compare <a> vs <b>` | An AI comparison |
| `summarize <text>` | An AI summary |
| `omniroute [status]` | Check if OmniRoute local gateway (port 20128) is online |
| `omniroute start` | Start OmniRoute background gateway |
| `omniroute sync` | Sync Claude Code model profiles |
| `omniroute web` | Launch the Web Dashboard Manager (`http://localhost:42100`) |
| `claude [profile]` | Launch a Claude Code terminal session (defaults to `auto-best-free`) |

File operations and `close` honour `JARVIS_DRY_RUN=1`, which previews the
action instead of performing it.

## Configuration

Everything tunable is read from environment variables, so you never have
to edit the code:

| Variable | Default | Purpose |
| --- | --- | --- |
| `JARVIS_DB_PATH` | `<project>/jarvis.db` | Where memories are stored |
| `JARVIS_DRY_RUN` | `0` | When `1`, launchers describe actions instead of performing them |
| `JARVIS_AI_PROVIDER` | `ollama` | `ollama`, `omniroute`, `openai`, or `none` |
| `JARVIS_AI_MODEL` | `llama3.2` | Model name for the local Ollama provider |
| `JARVIS_AI_TIMEOUT` | `30` | Request timeout (seconds) |
| `JARVIS_OMNIROUTE_HOST` | `http://localhost:20128/v1` | OmniRoute gateway address |
| `JARVIS_OMNIROUTE_MODEL` | `auto-best-free` | Active model profile for OmniRoute |
| `JARVIS_OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `OPENAI_API_KEY` | *(unset)* | Required for the OpenAI provider |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name for the OpenAI provider |
| `JARVIS_SYSTEM_PROMPT` | *(built-in)* | Override the assistant's persona |

## Optional features

These bring no required dependencies; install them only if you want the
feature. See `requirements-optional.txt` for the full list.

**AI conversation (v0.7 + OmniRoute).** You can route queries through:
* **OmniRoute** (330+ multi-provider profiles including free auto-routers, Gemini, Kiro, Nvidia NIM):
  ```bash
  export JARVIS_AI_PROVIDER=omniroute
  python main.py
  JARVIS > omniroute start
  JARVIS > ask what are Python metaclasses?
  ```
* **Ollama** (local offline, default):
  ```bash
  ollama pull llama3.2
  python main.py
  JARVIS > who are you
  ```
* **OpenAI / OpenAI-compatible**:
  ```bash
  export JARVIS_AI_PROVIDER=openai
  export OPENAI_API_KEY=sk-...
  ```

**OmniRoute Web Manager & 1-Click Launchers.**
* `Launch-OmniRoute-Web.bat`: Launches the dark-themed Web Dashboard on `http://localhost:42100` to browse 330+ profiles, check gateway health, and launch agent sessions.
* `Launch-Claude-Free.bat`: 1-click shortcut for an instant Claude Code coding session using `auto-best-free`.
* `Launch-Claude-MetaCombo.bat`: 1-click shortcut for a Claude Code session using `meta-combo-ai`.

**Voice (v0.6).**

```bash
pip install SpeechRecognition PyAudio pyttsx3
python main.py --voice
```

**Vision / OCR (v0.8).**

```bash
pip install mss pillow pytesseract   # also install the Tesseract engine
python main.py
JARVIS > screen        # read on-screen text
JARVIS > screenshot    # save a screenshot to your home folder
```

## Automation (scheduling)

JARVIS doesn't run a background daemon; instead it keeps your schedules in
its database and runs whatever is due when you call:

```bash
python main.py --run-due
```

Register schedules from inside JARVIS:

```text
JARVIS > schedule backup ~/notes every day at 22:00
Scheduled #1: 'backup ~/notes' — every day at 22:00.
JARVIS > schedule clean ~/Downloads every sunday at 09:00
JARVIS > schedules
1. backup ~/notes — every day at 22:00  (never run)
2. clean ~/Downloads — every sunday at 09:00  (never run)
```

Then let your operating system call `--run-due` periodically. On
Linux/macOS, an hourly cron entry is enough — the period check makes sure
each job only fires once per its window:

```cron
0 * * * * cd /path/to/AI-Companion && /path/to/venv/bin/python main.py --run-due
```

On Windows, create a Task Scheduler task that runs the same command on an
hourly trigger. Supported recurrences are `every hour`, `every day [at
HH:MM]`, and `every <weekday> [at HH:MM]`.

## Testing

```bash
pip install pytest
pytest
```

The suite uses injected fakes and a throwaway database, so it never opens
a browser, launches an app, hits the network, or touches your real
`jarvis.db`.

## Project layout

```text
AI-Companion/
├── main.py              # entry point + REPL / --once / --voice / --run-due
├── config/
│   └── settings.py      # env-driven configuration
├── core/
│   ├── brain.py         # parse -> route -> execute (+ history recorder)
│   ├── command_parser.py
│   ├── intent_router.py
│   ├── registry.py      # the skill plugin layer
│   ├── skill_manager.py
│   ├── bootstrap.py     # wires the real skills together
│   ├── dates.py         # natural due-date parsing
│   ├── schedule.py      # recurrence specs for automation
│   └── types.py
├── memory/              # one SQLite file, several small stores
│   ├── store.py         # shared connection helpers
│   ├── database.py      # notes
│   ├── prefs.py         # preferences
│   ├── tasks.py         # tasks
│   ├── history.py       # conversation log
│   └── schedules.py     # scheduled commands
├── skills/
│   ├── time_skill.py
│   ├── memory_skill.py      # notes
│   ├── prefs_skill.py       # preferences
│   ├── history_skill.py     # conversation log
│   ├── system_skill.py
│   ├── process_skill.py     # close / list processes
│   ├── app_skill.py         # cross-platform launcher
│   ├── web_skill.py         # website opener
│   ├── open_skill.py        # `open` = apps + websites
│   ├── files_skill.py       # safe file management
│   ├── task_skill.py        # planning agent
│   ├── schedule_skill.py    # automation agent
│   ├── code_skill.py        # project/class scaffolding
│   ├── research_skill.py    # AI-backed research
│   ├── ai_skill.py          # AI fallback (Ollama / OpenAI)
│   └── vision_skill.py
├── voice/
│   └── listener.py
└── tests/
```

## Adding a skill

1. Create a class in `skills/` that subclasses `Skill`, sets `triggers`
   and `help`, and implements `handle`.
2. Register it on one line in `core/bootstrap.py`.

The router and help text pick it up automatically — no other file needs
to change.

See [`ROADMAP.md`](ROADMAP.md) for version history and what's next.
