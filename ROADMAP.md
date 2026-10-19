# JARVIS Roadmap

Status of every planned version. Items marked ✅ are implemented in this
build.

## Shipped

### ✅ v0.1 — Core architecture
Brain, Intent Router, Skill Manager, Time skill.
*Improved:* the router/manager are now decoupled through a **skill
registry**, so adding a skill no longer means editing them.

### ✅ v0.2 — Persistent memory
SQLite-backed `remember` / `recall`.
*Improved:* the database takes an explicit path (no longer tied to the
working directory), creates parent folders, and returns typed rows.

### ✅ v0.2.1 — Forget memory
`forget <id>`, with validation for non-numeric and missing ids.
*Added:* `search <text>` for filtering notes.

### ✅ v0.3 — System monitoring
`cpu`, `ram`, `status`.
*Improved:* CPU sampling no longer blocks for a second per call; `disk`,
`battery` and `uptime` were added; `psutil` is now optional and degrades
gracefully.

### ✅ v0.4 — Basic application launcher
`open notepad`, `open calculator`.

### ✅ v0.4.1 — Smart application launcher *(the roadmap bug — fixed)*
**Problem:** the original launcher searched `C:\Program Files` for an
`.exe`, descended into the ACL-locked `C:\Program Files\WindowsApps`
folder, and crashed with `PermissionError: [WinError 5] Access is
denied`. Walking all of Program Files was also slow.

**Fix:** stop chasing executables. Discover applications the reliable
way and launch through the OS:

- **Windows** — Start Menu `.lnk` / `.url` shortcuts (ProgramData and
  per-user AppData), launched with `os.startfile` (this also handles the
  Store apps the old method choked on).
- **macOS** — `.app` bundles, launched with `open`.
- **Linux** — `.desktop` entries, launched with `gtk-launch` / `gio`.

Names are matched fuzzily (`open chrome` → "Google Chrome"), discovery
is cached, and there is no hard-coded app list.

### ✅ v0.5 — Website launcher
`open google`, `open github`, `open youtube.com`, `open chatgpt.com`.
The `open` command resolves apps vs. websites automatically; `website`
forces the browser.

### ✅ v0.6 — Voice assistant *(optional)*
Microphone input, speech recognition, and spoken replies via
`SpeechRecognition` + `pyttsx3`. Imported lazily and degrades gracefully
when the packages or a microphone aren't present. Run with
`python main.py --voice`.

### ✅ v0.7 — AI integration
Natural conversation through a local **Ollama** model (default, offline)
or any **OpenAI-compatible** endpoint. No extra Python packages required
(it uses the standard library). Unrecognised input is routed here, and a
clear setup message is shown when no provider is reachable.

### ✅ v0.8 — Vision *(optional)*
`screen` / `screenshot` — screen capture with `mss` + Pillow and OCR via
`pytesseract`. Optional and graceful when dependencies or a display are
missing.

### ✅ v0.9 — The agent expansion
Built toward the multi-agent vision in `PROJECT_JARVIS.md`. Each agent is
a group of skills on the same plugin architecture; the build grew from 5
capabilities to 14 while staying fully tested (157 tests).

- **Memory agent** — added **preferences** (`set` / `get` / `prefs` /
  `unset`) and a persistent **conversation history** (`history`) that
  every turn is recorded to, alongside the existing notes.
- **Planning agent** — a task list with natural due dates (`task … due
  friday`), completion (`done <id>`) and an `agenda` view.
- **Computer control** — safe, non-destructive **file management** (`ls`,
  `find`, `move`, `copy`, `organize`, `clean`, `backup`) and **process
  control** (`close`, `processes`). All dry-run aware.
- **Automation agent** — a real **scheduler engine**: recurrence-spec
  parsing, persisted `schedule` / `schedules` / `unschedule`, and a
  `--run-due` mode meant to be driven by cron / Task Scheduler. (The
  background-daemon half of the original v0.9 idea is intentionally left
  to the OS scheduler rather than reinvented.)
- **Coding agent** — project/class **scaffolding** (`scaffold python …`,
  `scaffold java …`); code explanation/debugging go through the AI skill.
- **Research agent** — `research` / `compare` / `summarize`, AI-backed.
  Uses the model's own knowledge (no live web fetch yet) and says so when
  the model isn't reachable.

### ✅ v0.9.5 — OmniRoute Multi-Model Gateway & Web Manager Integration
- **OmniRoute Gateway Provider** — native integration with OmniRoute (`http://localhost:20128/v1`) giving JARVIS instant access to 330+ AI model profiles (free auto-routers, Gemini, Antigravity, Kiro, Nvidia NIM).
- **Web Desktop Manager** — integrated Node.js browser dashboard (`http://localhost:42100`) to view gateway status, search profiles, and launch agent sessions.
- **Claude Code Agent Launchers** — 1-click batch/PowerShell launchers (`Launch-Claude-Free.bat`, `Launch-Claude-MetaCombo.bat`) and CLI command `claude [profile]`.
- **OmniRoute Skills** — `omniroute status`, `omniroute start`, `omniroute sync`, `omniroute web`.

## Next

### v0.10 — Reasoning & richer automation
- LLM-driven **tool selection** so free-form requests can route to the
  right skill (Phase 5 of the vision).
- Live **web research** for the research agent (fetch + summarise real
  sources).
- Workflow macros: named multi-step jobs and command chaining.

### Ideas beyond
- Per-skill configuration and enable/disable switches
- Plugin discovery from a `skills/` drop-in folder
- Seeding the AI skill with persisted conversation history

## Long-term vision

A fully featured local assistant that can remember information and
preferences, plan tasks, launch and close applications, manage files,
monitor the system, open websites, converse naturally, understand images,
scaffold code, research topics and automate everyday work on a
schedule — all running on your own machine, and expandable forever
through one-line skill registration.
