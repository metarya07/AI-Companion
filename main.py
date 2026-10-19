"""JARVIS entry point.

Run it interactively:

    python main.py

Run a single command and exit:

    python main.py --once "status"

Start in voice mode (needs the optional voice packages):

    python main.py --voice

Run any scheduled commands that are due (intended for cron / Task
Scheduler):

    python main.py --run-due
"""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import List, Optional

from config.settings import Settings
from core import __version__
from core.brain import Brain
from core.schedule import parse_spec
from memory.schedules import ScheduleStore

BANNER = f"=== JARVIS v{__version__} ===  (type 'help', or 'exit' to quit)"


def run_repl(brain: Brain) -> None:
    print(BANNER)
    while True:
        try:
            user_input = input("JARVIS > ")
        except (EOFError, KeyboardInterrupt):
            # Ctrl-D / Ctrl-C used to dump a traceback; now we exit cleanly.
            print("\nGoodbye.")
            return

        response = brain.process(user_input)
        if response.text:
            print(response.text)
        if response.should_exit:
            return


def run_once(brain: Brain, command: str) -> None:
    response = brain.process(command)
    if response.text:
        print(response.text)


def run_voice(brain: Brain) -> None:
    try:
        from voice.listener import VoiceListener, VoiceUnavailable
    except ImportError:  # pragma: no cover - defensive
        print("Voice support isn't installed.")
        return

    try:
        listener = VoiceListener()
    except VoiceUnavailable as exc:
        print(str(exc))
        return

    print(f"{BANNER}\nVoice mode active - say 'exit' to quit.")
    while True:  # pragma: no cover - requires a microphone
        try:
            spoken = listener.listen_once()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        if not spoken:
            continue
        print(f"You: {spoken}")
        response = brain.process(spoken)
        if response.text:
            print(response.text)
            listener.speak(response.text)
        if response.should_exit:
            return


def run_due(brain: Brain, settings: Settings, now: Optional[datetime] = None) -> int:
    """Run every scheduled command whose period has elapsed. Returns count."""
    now = now or datetime.now()
    store = ScheduleStore(settings.db_path)
    schedules = store.all()
    if not schedules:
        print("No schedules registered.")
        return 0

    ran = 0
    for sched in schedules:
        spec = parse_spec(sched.spec)
        if spec is None:
            continue
        last = datetime.fromisoformat(sched.last_run) if sched.last_run else None
        if spec.should_run(last, now):
            print(f"[run-due] {sched.command}  ({sched.spec})")
            response = brain.process(sched.command)
            if response.text:
                print(response.text)
            store.mark_run(sched.id, now.isoformat())
            ran += 1

    print(f"Ran {ran} scheduled command(s)." if ran else "Nothing due right now.")
    return ran


import webbrowser
from apps.web.server import create_app_server


def run_gui() -> None:
    """Start the JARVIS Native Windows Desktop GUI Application."""
    from apps.desktop.gui_app import launch_native_app
    launch_native_app()


def run_app(settings: Settings, host: str = "127.0.0.1", port: int = 5050, open_browser: bool = True) -> None:
    """Start the JARVIS Desktop Web App & Control Center HTTP server."""
    url = f"http://{host}:{port}"
    print(f"\n========================================================")
    print(f"  JARVIS Desktop Application & Control Center")
    print(f"  Version: {__version__}")
    print(f"  Running at: {url}")
    print(f"  Press Ctrl+C to stop.")
    print(f"========================================================\n")

    server = create_app_server(settings, host=host, port=port)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except (KeyboardInterrupt, EOFError):
        print("\nStopping JARVIS App Server...")
        server.shutdown()
        print("Goodbye.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis", description="JARVIS - a local AI desktop assistant."
    )
    parser.add_argument("--gui", "--desktop", action="store_true", help="launch the native Windows desktop app")
    parser.add_argument("--app", "--ui", "--web", action="store_true", help="launch the JARVIS desktop web app")
    parser.add_argument("--port", type=int, default=5050, help="port for the desktop web app (default: 5050)")
    parser.add_argument("--no-browser", action="store_true", help="don't automatically open browser in app mode")
    parser.add_argument("--once", metavar="COMMAND", help="run one command and exit")
    parser.add_argument("--voice", action="store_true", help="start in voice mode")
    parser.add_argument(
        "--run-due", action="store_true", help="run scheduled commands that are due"
    )
    parser.add_argument(
        "--version", action="store_true", help="print the version and exit"
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.version:
        print(f"JARVIS {__version__}")
        return 0

    settings = Settings.from_env()

    if args.gui:
        run_gui()
        return 0

    if args.app:
        run_app(settings, port=args.port, open_browser=not args.no_browser)
        return 0

    brain = Brain.create(settings)

    if args.run_due:
        run_due(brain, settings)
    elif args.once is not None:
        run_once(brain, args.once)
    elif args.voice:
        run_voice(brain)
    else:
        run_repl(brain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
