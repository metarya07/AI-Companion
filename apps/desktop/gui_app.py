# -*- coding: utf-8 -*-
"""JARVIS Native Windows Desktop Application — Obsidian Brain Neural Network Edition.

A standalone native Windows application providing a complete Obsidian-styled
Knowledge Vault interface:
- Real Obsidian Markdown Vault (`vault/`) integration
- Interactive Knowledge & Neural Graph View
- Markdown Note Editor & File Tree Explorer
- OmniRoute Multi-Model AI Chat Console
- 1-Click Native Obsidian Launcher
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from core import __version__
from core.bootstrap import build_brain
from memory.database import Database
from memory.tasks import TaskStore
from memory.vault import VaultManager, VaultNote
from skills.omniroute_skill import is_omniroute_online, get_claude_executable

try:
    import psutil
except ImportError:
    psutil = None

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

if not HAS_CTK:
    raise ImportError("customtkinter is required. Run: pip install customtkinter")

# ─── Obsidian Dark Palette ───────────────────────────────────────────────────
OBS = {
    "bg":          "#0d0d12",
    "sidebar":     "#111118",
    "surface":     "#16161f",
    "surface2":    "#1c1c28",
    "surface3":    "#222233",
    "border":      "#2a2740",
    "purple":      "#7c3aed",
    "purple_mid":  "#8b5cf6",
    "lavender":    "#a78bfa",
    "glow":        "#c4b5fd",
    "text":        "#e8e6f0",
    "text_dim":    "#8b87a8",
    "text_faint":  "#555273",
    "green":       "#4ade80",
    "amber":       "#fbbf24",
    "red":         "#f87171",
    "cyan":        "#22d3ee",
}

ctk.set_appearance_mode("Dark")


# ─── Full Interactive Obsidian Knowledge Graph Canvas ────────────────────────

# ─── Full Interactive Obsidian Knowledge Graph Canvas (Physics & Zoom) ────────

class InteractiveGraphCanvas(tk.Canvas):
    """Interactive Knowledge Graph visualizer with Obsidian-grade physics simulation,

    smooth mouse-wheel zooming, canvas panning, and node dragging.
    """

    def __init__(self, parent, on_node_click=None, **kwargs):
        super().__init__(
            parent,
            bg=OBS["bg"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.on_node_click = on_node_click
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Tuple[str, str]] = []
        self._hovered_node: Optional[str] = None
        self._selected_node: Optional[str] = None
        self._dragged_node: Optional[str] = None
        self._drag_start_screen = (0, 0)
        self._is_panning: bool = False
        self._pan_start_screen = (0, 0)

        # Camera
        self._zoom: float = 0.95
        self._pan_x: float = 0.0
        self._pan_y: float = 0.0

        # Animation & Physics
        self._t: float = 0.0
        self._running: bool = True
        self._physics_enabled: bool = True
        self._omni_online: bool = False

        # Event Bindings
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows
        self.bind("<Button-4>", lambda e: self._zoom_step(1.15, e.x, e.y))  # Linux
        self.bind("<Button-5>", lambda e: self._zoom_step(1 / 1.15, e.x, e.y))

        # Right click drag to pan as well
        self.bind("<ButtonPress-3>", self._on_right_down)
        self.bind("<B3-Motion>", self._on_right_drag)
        self.bind("<ButtonRelease-3>", lambda _: setattr(self, "_is_panning", False))

        self._animate()

    def set_graph_data(self, data: Dict[str, Any], omni_online: bool = False):
        self._omni_online = omni_online
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])

        new_nodes: Dict[str, Dict[str, Any]] = {}
        count = len(raw_nodes)

        for i, n in enumerate(raw_nodes):
            nid = n["id"]
            if nid in self._nodes:
                # Retain existing position and velocity
                node_obj = self._nodes[nid]
                node_obj.update(n)
                new_nodes[nid] = node_obj
            else:
                # Radial spread layout
                if nid == "ai-core":
                    wx, wy = 0.0, 0.0
                else:
                    angle = (i / max(1, count)) * 2 * math.pi
                    group = n.get("group", "")
                    dist = 180.0 + ((hash(nid) % 180) - 90)
                    if group in ("Drive-A", "Projects"):
                        dist = 220.0
                    elif group in ("Drive-C", "Tools"):
                        dist = 280.0
                    elif group == "tags":
                        dist = 340.0
                    wx = math.cos(angle) * dist
                    wy = math.sin(angle) * dist

                new_nodes[nid] = {
                    "id": nid,
                    "x": wx,
                    "y": wy,
                    "vx": random.uniform(-0.5, 0.5),
                    "vy": random.uniform(-0.5, 0.5),
                    "r": float(n.get("size", 12)),
                    "group": n.get("group", ""),
                    "label": n.get("label", nid),
                    "tags": n.get("tags", []),
                    "rel_path": n.get("rel_path", ""),
                }

        self._nodes = new_nodes
        self._edges = [(e["source"], e["target"]) for e in raw_edges]

    def _on_resize(self, event=None):
        pass

    # ── Camera Coordinate Transforms ──────────────────────────────────────────

    def _world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        cx, cy = w / 2.0, h / 2.0
        sx = cx + (wx + self._pan_x) * self._zoom
        sy = cy + (wy + self._pan_y) * self._zoom
        return sx, sy

    def _screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        cx, cy = w / 2.0, h / 2.0
        wx = (sx - cx) / self._zoom - self._pan_x
        wy = (sy - cy) / self._zoom - self._pan_y
        return wx, wy

    # ── Mouse & Zoom Handlers ─────────────────────────────────────────────────

    def _find_node_at_screen(self, sx: float, sy: float) -> Optional[str]:
        for nid, n in self._nodes.items():
            nsx, nsy = self._world_to_screen(n["x"], n["y"])
            hit_r = max(10, n["r"] * self._zoom) + 6
            if math.hypot(sx - nsx, sy - nsy) <= hit_r:
                return nid
        return None

    def _on_mouse_move(self, event):
        if not self._dragged_node and not self._is_panning:
            prev = self._hovered_node
            self._hovered_node = self._find_node_at_screen(event.x, event.y)
            if prev != self._hovered_node:
                self.config(cursor="hand2" if self._hovered_node else "")

    def _on_mouse_down(self, event):
        self._drag_start_screen = (event.x, event.y)
        node_hit = self._find_node_at_screen(event.x, event.y)
        if node_hit:
            self._dragged_node = node_hit
            self._selected_node = node_hit
        else:
            self._is_panning = True
            self._pan_start_screen = (event.x, event.y)

    def _on_right_down(self, event):
        self._is_panning = True
        self._pan_start_screen = (event.x, event.y)

    def _on_mouse_drag(self, event):
        if self._dragged_node and self._dragged_node in self._nodes:
            wx, wy = self._screen_to_world(event.x, event.y)
            n = self._nodes[self._dragged_node]
            n["x"] = wx
            n["y"] = wy
            n["vx"] = 0.0
            n["vy"] = 0.0
        elif self._is_panning:
            dx = event.x - self._pan_start_screen[0]
            dy = event.y - self._pan_start_screen[1]
            self._pan_x += dx / self._zoom
            self._pan_y += dy / self._zoom
            self._pan_start_screen = (event.x, event.y)

    def _on_right_drag(self, event):
        if self._is_panning:
            dx = event.x - self._pan_start_screen[0]
            dy = event.y - self._pan_start_screen[1]
            self._pan_x += dx / self._zoom
            self._pan_y += dy / self._zoom
            self._pan_start_screen = (event.x, event.y)

    def _on_mouse_up(self, event):
        # Click detection (if travel < 5px)
        travel = math.hypot(event.x - self._drag_start_screen[0], event.y - self._drag_start_screen[1])
        if travel < 5.0 and self._dragged_node and self._dragged_node != "ai-core":
            if self.on_node_click:
                self.on_node_click(self._dragged_node)

        self._dragged_node = None
        self._is_panning = False

    def _on_mouse_wheel(self, event):
        # Windows event.delta is +/- 120
        factor = 1.15 if event.delta > 0 else (1 / 1.15)
        self._zoom_step(factor, event.x, event.y)

    def _zoom_step(self, factor: float, sx: float, sy: float):
        old_zoom = self._zoom
        new_zoom = max(0.15, min(4.0, old_zoom * factor))
        if new_zoom == old_zoom:
            return

        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        cx, cy = w / 2.0, h / 2.0

        # Preserve point under cursor
        wx_cursor = (sx - cx) / old_zoom - self._pan_x
        wy_cursor = (sy - cy) / old_zoom - self._pan_y

        self._zoom = new_zoom
        self._pan_x = (sx - cx) / new_zoom - wx_cursor
        self._pan_y = (sy - cy) / new_zoom - wy_cursor

    def zoom_in(self):
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        self._zoom_step(1.2, w / 2.0, h / 2.0)

    def zoom_out(self):
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        self._zoom_step(1 / 1.2, w / 2.0, h / 2.0)

    def reset_view(self):
        self._zoom = 0.95
        self._pan_x = 0.0
        self._pan_y = 0.0

    def toggle_physics(self) -> bool:
        self._physics_enabled = not self._physics_enabled
        return self._physics_enabled

    # ── Force-Directed Physics Simulation ─────────────────────────────────────

    def _physics_step(self):
        if not self._physics_enabled:
            return

        nodes = list(self._nodes.values())
        count = len(nodes)

        # 1. Repulsion between all node pairs (Coulomb force)
        for i in range(count):
            a = nodes[i]
            for j in range(i + 1, count):
                b = nodes[j]
                dx = b["x"] - a["x"]
                dy = b["y"] - a["y"]
                dist = math.hypot(dx, dy) + 0.1
                if dist < 500:
                    force = 1200.0 / (dist * dist + 80.0)
                    fx = (dx / dist) * force
                    fy = (dy / dist) * force
                    if a["id"] != self._dragged_node:
                        a["vx"] -= fx
                        a["vy"] -= fy
                    if b["id"] != self._dragged_node:
                        b["vx"] += fx
                        b["vy"] += fy

        # 2. Spring attraction along edges (Hooke's law)
        for src_id, dst_id in self._edges:
            if src_id in self._nodes and dst_id in self._nodes:
                a = self._nodes[src_id]
                b = self._nodes[dst_id]
                dx = b["x"] - a["x"]
                dy = b["y"] - a["y"]
                dist = math.hypot(dx, dy) + 0.1
                target_dist = 130.0
                disp = dist - target_dist
                force = disp * 0.015
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                if a["id"] != self._dragged_node:
                    a["vx"] += fx
                    a["vy"] += fy
                if b["id"] != self._dragged_node:
                    b["vx"] -= fx
                    b["vy"] -= fy

        # 3. Center gravity (pull gently toward origin)
        for n in nodes:
            if n["id"] != self._dragged_node:
                n["vx"] -= n["x"] * 0.003
                n["vy"] -= n["y"] * 0.003

                # Velocity damping & speed limit
                n["vx"] *= 0.86
                n["vy"] *= 0.86
                speed = math.hypot(n["vx"], n["vy"])
                if speed > 18.0:
                    n["vx"] = (n["vx"] / speed) * 18.0
                    n["vy"] = (n["vy"] / speed) * 18.0

                n["x"] += n["vx"]
                n["y"] += n["vy"]

    # ── Canvas Drawing ────────────────────────────────────────────────────────

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600

        # Dynamic background grid based on zoom & pan
        grid_size = max(24, int(40 * self._zoom))
        offset_x = int((self._pan_x * self._zoom + w / 2.0) % grid_size)
        offset_y = int((self._pan_y * self._zoom + h / 2.0) % grid_size)

        for gx in range(offset_x, w, grid_size):
            for gy in range(offset_y, h, grid_size):
                self.create_oval(gx, gy, gx + 1, gy + 1, fill="#1c1a2e", outline="")

        # Draw Edges
        for src_id, dst_id in self._edges:
            if src_id in self._nodes and dst_id in self._nodes:
                a = self._nodes[src_id]
                b = self._nodes[dst_id]
                sx, sy = self._world_to_screen(a["x"], a["y"])
                dx, dy = self._world_to_screen(b["x"], b["y"])

                is_active = (src_id in (self._hovered_node, self._selected_node) or
                             dst_id in (self._hovered_node, self._selected_node))
                col = OBS["lavender"] if is_active else "#2b2742"
                width = max(1.0, 2.0 * self._zoom if is_active else 1.0 * self._zoom)
                self.create_line(sx, sy, dx, dy, fill=col, width=width, smooth=True)

                # Travelling synaptic pulse
                if src_id == "ai-core" or is_active:
                    frac = (self._t * 0.7 + (hash(src_id + dst_id) % 50) / 50.0) % 1.0
                    px = sx + (dx - sx) * frac
                    py = sy + (dy - sy) * frac
                    pr = max(1.5, 2.5 * self._zoom)
                    self.create_oval(px - pr, py - pr, px + pr, py + pr, fill=OBS["glow"], outline="")

        # Draw Nodes
        for nid, n in self._nodes.items():
            sx, sy = self._world_to_screen(n["x"], n["y"])
            r = max(3.0, n["r"] * self._zoom)
            group = n["group"]
            is_hover = (nid == self._hovered_node)
            is_sel   = (nid == self._selected_node)

            # Node Color Theme
            if nid == "ai-core":
                base_col = OBS["green"] if self._omni_online else OBS["purple"]
                glow_col = OBS["glow"]
            elif group == "Daily":
                base_col = OBS["amber"]
                glow_col = "#fde68a"
            elif group in ("Drive-A", "Projects"):
                base_col = OBS["lavender"]
                glow_col = "#ddd6fe"
            elif group in ("Drive-C", "Tools"):
                base_col = OBS["cyan"]
                glow_col = "#a5f3fc"
            elif group == "Tasks":
                base_col = "#38bdf8"
                glow_col = "#bae6fd"
            elif group == "Memories":
                base_col = OBS["purple_mid"]
                glow_col = OBS["lavender"]
            elif group == "tags":
                base_col = OBS["text_dim"]
                glow_col = OBS["text"]
            else:
                base_col = OBS["purple"]
                glow_col = OBS["glow"]

            # Glow aura
            if is_hover or is_sel or nid == "ai-core":
                glow_r = r + (8 if is_hover else 4) * self._zoom
                self.create_oval(
                    sx - glow_r, sy - glow_r,
                    sx + glow_r, sy + glow_r,
                    outline=glow_col, fill="", width=max(1, int(1.5 * self._zoom)),
                )

            # Node body
            self.create_oval(
                sx - r, sy - r,
                sx + r, sy + r,
                fill=base_col, outline=OBS["bg"], width=max(1, int(2 * self._zoom)),
            )

            # Label rendering with smart zoom thresholds
            if self._zoom > 0.45 or is_hover or is_sel or nid == "ai-core":
                label = n.get("label", nid)
                if len(label) > 22 and nid != "ai-core" and not is_hover:
                    label = label[:20] + ".."
                font_size = max(7, min(12, int(9 * self._zoom)))
                text_col = OBS["text"] if (is_hover or is_sel) else OBS["text_dim"]
                self.create_text(
                    sx, sy + r + (8 * self._zoom),
                    text=label,
                    font=("Segoe UI", font_size, "bold" if (is_hover or is_sel) else "normal"),
                    fill=text_col,
                )

    def _animate(self):
        if not self._running:
            return
        # Only animate & compute physics when the Graph View is actually visible on screen!
        try:
            if not self.winfo_ismapped():
                self.after(250, self._animate)
                return
        except Exception:
            pass

        self._t += 0.04
        self._physics_step()
        self._draw()
        self.after(50, self._animate)  # Smooth 20 FPS with minimal CPU usage

    def destroy(self):
        self._running = False
        super().destroy()


# ─── Sidebar Mini Neural Canvas ──────────────────────────────────────────────

class SidebarNeuralMini(tk.Canvas):
    """Compact animated synaptic brain widget for the left sidebar."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=OBS["sidebar"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self._t = 0.0
        self._running = True
        self._animate()

    def _animate(self):
        if not self._running:
            return
        try:
            if not self.winfo_ismapped():
                self.after(300, self._animate)
                return
        except Exception:
            pass

        self._t += 0.04
        self.delete("all")
        w = self.winfo_width() or 220
        h = self.winfo_height() or 80
        cx, cy = w / 2.0, h / 2.0

        # Draw 5 orbital synaptic dots
        for i in range(5):
            angle = self._t * 0.8 + (i * (2 * math.pi / 5))
            rad_x = 70 + math.sin(self._t * 1.2 + i) * 8
            rad_y = 20 + math.cos(self._t * 0.9 + i) * 4
            x = cx + math.cos(angle) * rad_x
            y = cy + math.sin(angle) * rad_y
            self.create_line(cx, cy, x, y, fill="#2b2742", width=1)
            self.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill=OBS["lavender"], outline="")

        # Central brain node
        pulse = 5 + math.sin(self._t * 2.0) * 1.5
        self.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill=OBS["purple"], outline=OBS["glow"])
        self.create_text(cx, cy, text="⬡", font=("Segoe UI", 9, "bold"), fill=OBS["text"])

        self.after(80, self._animate)  # ~12 FPS lightweight sidebar animation

    def destroy(self):
        self._running = False
        super().destroy()


# ─── Main Desktop Application ─────────────────────────────────────────────────

class JarvisNativeApp(ctk.CTk):
    """Complete Obsidian Knowledge Vault & Neural Desktop Interface."""

    def __init__(self):
        super().__init__()

        self.settings = Settings.from_env()
        self.brain   = build_brain(self.settings)
        self.vault   = VaultManager(self.settings.vault_path)

        self.title(f"JARVIS  ·  Obsidian Neural Knowledge Base  ·  v{__version__}")
        self.geometry("1280x800")
        self.minsize(1050, 680)
        self.configure(fg_color=OBS["bg"])

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # State
        self._active_view = "editor"
        self._active_note: Optional[VaultNote] = None
        self._omni_online = False
        self.available_models = self._load_omniroute_models()
        self.current_model    = self.settings.omniroute_model or "auto-best-free"

        # Auto-start OmniRoute if configured
        if not is_omniroute_online() and self.settings.omniroute_auto_start:
            self._start_omniroute_server()

        self._build_top_bar()
        self._build_sidebar()
        self._build_content()
        self._build_status_bar()

        # Select initial note & view
        notes = self.vault.list_notes()
        if notes:
            self._open_note(notes[0])
        else:
            self.select_view("editor")

        self._start_telemetry()

    def _load_omniroute_models(self) -> List[str]:
        profiles_dir = Path.home() / ".claude" / "profiles"
        profiles = []
        if profiles_dir.exists():
            profiles = [d.name for d in profiles_dir.iterdir() if d.is_dir()]
        return sorted(profiles) or [
            "auto-best-free", "auto-best-fast", "auto-best-coding",
            "meta-combo-ai", "kiro-glm-5", "antigravity-flash",
        ]

    def _start_omniroute_server(self):
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "/min", "powershell", "-NoExit", "-Command", "omniroute serve"],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
        except Exception as e:
            print(f"Auto-start OmniRoute failed: {e}")

    # ── TOP APP BAR ───────────────────────────────────────────────────────────

    def _build_top_bar(self):
        top = ctk.CTkFrame(self, height=46, fg_color=OBS["sidebar"], corner_radius=0)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.grid_propagate(False)

        # Logo & Vault Title
        brand = ctk.CTkFrame(top, fg_color="transparent")
        brand.pack(side="left", padx=16)

        ctk.CTkLabel(
            brand,
            text="⬡  JARVIS VAULT",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(side="left")

        ctk.CTkLabel(
            brand,
            text=f" ·  {self.vault.vault_path.name}",
            font=ctk.CTkFont(size=11),
            text_color=OBS["text_dim"],
        ).pack(side="left", padx=6)

        # Center View Switcher Tabs
        tabs_frame = ctk.CTkFrame(top, fg_color="transparent")
        tabs_frame.pack(side="left", padx=30)

        self._top_tabs = {}
        tab_specs = [
            ("editor", "📝  Note Editor"),
            ("graph",  "🧠  Graph View"),
            ("chat",   "💬  AI Console"),
            ("tasks",  "📋  Task Matrix"),
            ("agent",  "🤖  Coding Agent"),
            ("settings", "⚙️  Settings"),
        ]
        for vid, label in tab_specs:
            btn = ctk.CTkButton(
                tabs_frame,
                text=label,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=OBS["purple"] if vid == "editor" else "transparent",
                hover_color=OBS["surface2"],
                text_color=OBS["text"] if vid == "editor" else OBS["text_dim"],
                command=lambda v=vid: self.select_view(v),
            )
            btn.pack(side="left", padx=2)
            self._top_tabs[vid] = btn

        # Right Action: 1-Click Launch Native Obsidian
        right_actions = ctk.CTkFrame(top, fg_color="transparent")
        right_actions.pack(side="right", padx=14)

        ctk.CTkButton(
            right_actions,
            text="🚀  Open in Obsidian",
            height=28,
            corner_radius=6,
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            border_width=1,
            border_color=OBS["border"],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=OBS["lavender"],
            command=lambda: self.vault.open_in_obsidian(self._active_note.rel_path if self._active_note else None),
        ).pack(side="right", padx=4)

    # ── SIDEBAR (FILE EXPLORER + TREE) ────────────────────────────────────────

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=OBS["sidebar"])
        sb.grid(row=1, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(2, weight=1)
        sb.grid_columnconfigure(0, weight=1)
        self._sidebar = sb

        # Sidebar Header Controls
        ctrl = ctk.CTkFrame(sb, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            ctrl,
            text="FILES & VAULT",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=OBS["text_dim"],
        ).pack(side="left")

        # + New Note button
        ctk.CTkButton(
            ctrl,
            text="+ Note",
            width=50,
            height=22,
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            command=self._new_note_dialog,
        ).pack(side="right", padx=2)

        # Daily note button
        ctk.CTkButton(
            ctrl,
            text="📅 Daily",
            width=52,
            height=22,
            corner_radius=4,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=self._open_daily_note,
        ).pack(side="right", padx=2)

        # Search Bar
        self._search_var = ctk.StringVar()
        self._search_entry = ctk.CTkEntry(
            sb,
            placeholder_text="🔍 Search vault notes…",
            height=28,
            corner_radius=6,
            fg_color=OBS["surface2"],
            border_color=OBS["border"],
            text_color=OBS["text"],
            placeholder_text_color=OBS["text_dim"],
            font=ctk.CTkFont(size=11),
            textvariable=self._search_var,
        )
        self._search_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self._search_entry.bind("<KeyRelease>", lambda _: self._refresh_file_tree())

        # File Tree Scrollable Area
        self._file_tree = ctk.CTkScrollableFrame(
            sb,
            fg_color="transparent",
            scrollbar_button_color=OBS["surface2"],
            scrollbar_button_hover_color=OBS["purple"],
        )
        self._file_tree.grid(row=2, column=0, sticky="nsew", padx=4, pady=0)

        # Sidebar Mini Neural Canvas
        self._mini_canvas = SidebarNeuralMini(sb, height=70)
        self._mini_canvas.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        # AI Profile Selector & Telemetry
        footer = ctk.CTkFrame(sb, fg_color=OBS["surface"], corner_radius=8)
        footer.grid(row=4, column=0, sticky="ew", padx=10, pady=(4, 10))

        # Model Selector
        self._model_var = ctk.StringVar(value=self.current_model)
        self._model_menu = ctk.CTkOptionMenu(
            footer,
            variable=self._model_var,
            values=self.available_models,
            command=self._on_model_change,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            button_color=OBS["purple"],
            text_color=OBS["text"],
        )
        self._model_menu.pack(fill="x", padx=8, pady=(8, 4))

        # OmniRoute status row
        omni_row = ctk.CTkFrame(footer, fg_color="transparent")
        omni_row.pack(fill="x", padx=8, pady=2)
        self._omni_dot = tk.Canvas(omni_row, width=8, height=8, bg=OBS["surface"], highlightthickness=0)
        self._omni_dot.pack(side="left", padx=(0, 4))
        self._omni_dot.create_oval(1, 1, 7, 7, fill=OBS["red"], outline="")
        self._omni_label = ctk.CTkLabel(
            omni_row,
            text="OmniRoute Offline",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=OBS["red"],
        )
        self._omni_label.pack(side="left")

        # CPU / RAM
        res_row = ctk.CTkFrame(footer, fg_color="transparent")
        res_row.pack(fill="x", padx=8, pady=(0, 4))
        self._lbl_cpu = ctk.CTkLabel(res_row, text="CPU: --%", font=ctk.CTkFont(size=9), text_color=OBS["text_dim"])
        self._lbl_cpu.pack(side="left")
        self._lbl_ram = ctk.CTkLabel(res_row, text="RAM: --%", font=ctk.CTkFont(size=9), text_color=OBS["text_dim"])
        self._lbl_ram.pack(side="right")

        # Quick Settings button
        ctk.CTkButton(
            footer,
            text="⚙️ Settings & Diagnostics",
            height=24,
            corner_radius=4,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            text_color=OBS["text_dim"],
            command=lambda: self.select_view("settings"),
        ).pack(fill="x", padx=8, pady=(2, 6))

        self._refresh_file_tree()

    def _refresh_file_tree(self):
        for w in self._file_tree.winfo_children():
            w.destroy()

        query = self._search_var.get().strip().lower()
        notes = self.vault.search_notes(query) if query else self.vault.list_notes()

        # Group by folder
        grouped: Dict[str, List[VaultNote]] = {}
        for n in notes:
            folder = n.folder or "Root"
            grouped.setdefault(folder, []).append(n)

        for folder_name in sorted(grouped.keys()):
            # Folder Header
            f_frame = ctk.CTkFrame(self._file_tree, fg_color="transparent")
            f_frame.pack(fill="x", pady=(4, 1))
            ctk.CTkLabel(
                f_frame,
                text=f"📁 {folder_name}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=OBS["lavender"],
                anchor="w",
            ).pack(side="left", padx=4)

            # Note Rows
            for note in grouped[folder_name]:
                is_active = (self._active_note and self._active_note.abs_path == note.abs_path)
                btn = ctk.CTkButton(
                    self._file_tree,
                    text=f"  📄 {note.title}",
                    anchor="w",
                    height=24,
                    corner_radius=4,
                    font=ctk.CTkFont(size=11),
                    fg_color=OBS["surface2"] if is_active else "transparent",
                    hover_color=OBS["surface"],
                    text_color=OBS["text"] if is_active else OBS["text_dim"],
                    command=lambda n=note: self._open_note(n),
                )
                btn.pack(fill="x", padx=(8, 2), pady=1)

    # ── WORKSPACE CONTENT VIEWS ───────────────────────────────────────────────

    def _build_content(self):
        self._views: Dict[str, ctk.CTkFrame] = {}

        self._views["editor"]   = self._build_editor_view()
        self._views["graph"]    = self._build_graph_view()
        self._views["chat"]     = self._build_chat_view()
        self._views["tasks"]    = self._build_tasks_view()
        self._views["agent"]    = self._build_agent_view()
        self._views["settings"] = self._build_settings_view()

        for v in self._views.values():
            v.grid(row=1, column=1, sticky="nsew")
            v.grid_remove()

    # ── 1. NOTE EDITOR VIEW ───────────────────────────────────────────────────

    def _build_editor_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=OBS["bg"], corner_radius=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Editor Header Row (Title + Actions)
        top_row = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=50)
        top_row.grid(row=0, column=0, sticky="ew")
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_propagate(False)

        self._note_title_entry = ctk.CTkEntry(
            top_row,
            placeholder_text="Note Title",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="transparent",
            border_width=0,
            text_color=OBS["lavender"],
        )
        self._note_title_entry.grid(row=0, column=0, padx=16, pady=8, sticky="ew")

        # Action Buttons on Right
        act = ctk.CTkFrame(top_row, fg_color="transparent")
        act.grid(row=0, column=1, padx=12, pady=8, sticky="e")

        ctk.CTkButton(
            act,
            text="💾 Save",
            width=70,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            command=self._save_current_note,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            act,
            text="🗑️ Delete",
            width=70,
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=OBS["surface2"],
            hover_color=OBS["red"],
            text_color=OBS["text_dim"],
            command=self._delete_current_note,
        ).pack(side="left", padx=4)

        # Note Metadata Bar
        meta_row = ctk.CTkFrame(frame, fg_color=OBS["surface2"], corner_radius=0, height=32)
        meta_row.grid(row=1, column=0, sticky="ew")
        meta_row.grid_propagate(False)

        self._meta_folder_lbl = ctk.CTkLabel(
            meta_row,
            text="📁 Folder: Ideas",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        )
        self._meta_folder_lbl.pack(side="left", padx=16)

        self._meta_tags_lbl = ctk.CTkLabel(
            meta_row,
            text="🏷️ Tags: none",
            font=ctk.CTkFont(size=10),
            text_color=OBS["lavender"],
        )
        self._meta_tags_lbl.pack(side="left", padx=16)

        self._meta_words_lbl = ctk.CTkLabel(
            meta_row,
            text="0 words  ·  0 chars",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        )
        self._meta_words_lbl.pack(side="right", padx=16)

        # Markdown Text Editor Pane
        self._editor_box = ctk.CTkTextbox(
            frame,
            fg_color=OBS["bg"],
            text_color=OBS["text"],
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=0,
            wrap="word",
            undo=True,
        )
        self._editor_box.grid(row=2, column=0, sticky="nsew", padx=16, pady=12)
        self._editor_box.bind("<KeyRelease>", lambda _: self._update_editor_stats())

        return frame

    def _open_note(self, note: VaultNote):
        self._active_note = note
        self._note_title_entry.delete(0, "end")
        self._note_title_entry.insert(0, note.title)

        self._meta_folder_lbl.configure(text=f"📁 Folder: {note.folder or 'Root'}")
        tags_str = " ".join(f"#{t}" for t in note.tags) if note.tags else "none"
        self._meta_tags_lbl.configure(text=f"🏷️ Tags: {tags_str}")

        self._editor_box.delete("1.0", "end")
        self._editor_box.insert("1.0", note.content)
        self._update_editor_stats()
        self.select_view("editor")
        self._refresh_file_tree()

    def _update_editor_stats(self):
        content = self._editor_box.get("1.0", "end-1c")
        words = len(content.split())
        chars = len(content)
        self._meta_words_lbl.configure(text=f"{words} words  ·  {chars} chars")
        if hasattr(self, "_sb_words"):
            self._sb_words.configure(text=f"{words} words")
            self._sb_chars.configure(text=f"{chars} chars")

    def _save_current_note(self):
        title = self._note_title_entry.get().strip() or "Untitled"
        content = self._editor_box.get("1.0", "end-1c")
        folder = self._active_note.folder if self._active_note else "Ideas"

        saved = self.vault.save_note(title=title, content=content, folder=folder)
        self._active_note = saved
        self._refresh_file_tree()
        if hasattr(self, "_graph_canvas"):
            self._graph_canvas.set_graph_data(self.vault.get_graph_data(), self._omni_online)

    def _delete_current_note(self):
        if not self._active_note:
            return
        self.vault.delete_note(self._active_note.abs_path)
        notes = self.vault.list_notes()
        if notes:
            self._open_note(notes[0])
        else:
            self._active_note = None
            self._editor_box.delete("1.0", "end")
            self._note_title_entry.delete(0, "end")
        self._refresh_file_tree()

    def _new_note_dialog(self):
        new_note = self.vault.save_note(
            title=f"New Note {datetime.now().strftime('%H%M%S')}",
            content="# New Note\n\nWrite your thoughts here...\n\n#ideas\n",
            folder="Ideas",
        )
        self._open_note(new_note)

    def _open_daily_note(self):
        daily = self.vault.get_daily_note(create_if_missing=True)
        self._open_note(daily)

    # ── 2. INTERACTIVE GRAPH VIEW ─────────────────────────────────────────────

    def _build_graph_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=OBS["bg"], corner_radius=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Graph Header Bar Controls
        header = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="🧠  Interactive Knowledge Graph",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(side="left", padx=16)

        ctk.CTkLabel(
            header,
            text="Scroll: Zoom · Drag: Pan / Move nodes · Click: Open",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        ).pack(side="left", padx=4)

        # Right Action Buttons
        act_frame = ctk.CTkFrame(header, fg_color="transparent")
        act_frame.pack(side="right", padx=12)

        ctk.CTkButton(
            act_frame,
            text="➕",
            width=30,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=lambda: self._graph_canvas.zoom_in() if hasattr(self, "_graph_canvas") else None,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            act_frame,
            text="➖",
            width=30,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=lambda: self._graph_canvas.zoom_out() if hasattr(self, "_graph_canvas") else None,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            act_frame,
            text="⟲ Reset",
            width=65,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=lambda: self._graph_canvas.reset_view() if hasattr(self, "_graph_canvas") else None,
        ).pack(side="left", padx=2)

        self._btn_physics = ctk.CTkButton(
            act_frame,
            text="⏸ Pause",
            width=65,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=self._toggle_graph_physics,
        )
        self._btn_physics.pack(side="left", padx=2)

        ctk.CTkButton(
            act_frame,
            text="🔄 Re-Index PC",
            width=90,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            command=self._rescan_pc_and_refresh,
        ).pack(side="left", padx=4)

        # Graph Canvas
        self._graph_canvas = InteractiveGraphCanvas(
            frame,
            on_node_click=self._on_graph_node_clicked,
        )
        self._graph_canvas.grid(row=1, column=0, sticky="nsew")
        self._refresh_graph_view()

        return frame

    def _toggle_graph_physics(self):
        if hasattr(self, "_graph_canvas"):
            is_active = self._graph_canvas.toggle_physics()
            self._btn_physics.configure(text="⏸ Pause" if is_active else "▶ Play")

    def _rescan_pc_and_refresh(self):
        from memory.pc_indexer import PCVaultIndexer
        indexer = PCVaultIndexer(self.vault)
        indexer.index_all()
        self._refresh_file_tree()
        self._refresh_graph_view()

    def _refresh_graph_view(self):
        if hasattr(self, "_graph_canvas"):
            self._graph_canvas.set_graph_data(self.vault.get_graph_data(), self._omni_online)

    def _on_graph_node_clicked(self, node_title: str):
        note = self.vault.get_note(node_title)
        if note:
            self._open_note(note)

    # ── 3. NEURAL AI CONSOLE ──────────────────────────────────────────────────

    def _build_chat_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=OBS["bg"], corner_radius=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="💬  OmniRoute Neural AI Console",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(side="left", padx=16)

        # Quick chips
        chips_frame = ctk.CTkFrame(header, fg_color="transparent")
        chips_frame.pack(side="right", padx=12)
        for chip in ["daily", "vault list", "status", "tasks", "time"]:
            ctk.CTkButton(
                chips_frame,
                text=chip,
                height=24,
                corner_radius=12,
                fg_color=OBS["surface2"],
                hover_color=OBS["purple"],
                text_color=OBS["text_dim"],
                font=ctk.CTkFont(size=10),
                command=lambda c=chip: self._send_async(c),
            ).pack(side="left", padx=3)

        # Messages Stream
        self._chat_stream = ctk.CTkScrollableFrame(
            frame,
            fg_color=OBS["bg"],
            corner_radius=0,
            scrollbar_button_color=OBS["purple"],
        )
        self._chat_stream.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Input Row
        input_row = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=58)
        input_row.grid(row=2, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        input_row.grid_propagate(False)

        self._chat_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Ask JARVIS or note thoughts — e.g. 'note Idea: AI memory system #ideas'",
            height=38,
            corner_radius=19,
            fg_color=OBS["surface2"],
            border_color=OBS["purple"],
            border_width=1,
            text_color=OBS["text"],
            placeholder_text_color=OBS["text_dim"],
            font=ctk.CTkFont(size=12),
        )
        self._chat_entry.grid(row=0, column=0, padx=(14, 8), pady=10, sticky="ew")
        self._chat_entry.bind("<Return>", lambda _: self._on_send())

        self._btn_send = ctk.CTkButton(
            input_row,
            text="Send  ›",
            width=80,
            height=38,
            corner_radius=19,
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            text_color=OBS["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_send,
        )
        self._btn_send.grid(row=0, column=1, padx=(0, 14), pady=10)

        self._append_msg(
            "JARVIS",
            f"Obsidian Knowledge Base active. Connected to `{self.current_model}`.\n"
            "You can manage notes (`note <title>: <content>`), inspect the vault (`vault list`), or ask questions.",
        )
        return frame

    def _append_msg(self, sender: str, text: str):
        is_user = sender == "You"
        outer = ctk.CTkFrame(self._chat_stream, fg_color="transparent")
        outer.pack(fill="x", padx=12, pady=4, anchor="e" if is_user else "w")

        card = ctk.CTkFrame(
            outer,
            fg_color=OBS["surface2"] if is_user else OBS["surface"],
            corner_radius=12,
            border_width=1,
            border_color=OBS["purple"] if not is_user else OBS["border"],
        )
        card.pack(anchor="e" if is_user else "w", padx=(60 if not is_user else 0, 0 if not is_user else 60))

        # Sender & Actions
        header_card = ctk.CTkFrame(card, fg_color="transparent")
        header_card.pack(fill="x", padx=14, pady=(8, 0))

        ctk.CTkLabel(
            header_card,
            text=sender,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=OBS["lavender"] if not is_user else OBS["text_dim"],
        ).pack(side="left")

        if not is_user:
            # Save AI response as a Vault Note button
            ctk.CTkButton(
                header_card,
                text="📌 Save to Vault",
                width=80,
                height=18,
                corner_radius=4,
                font=ctk.CTkFont(size=9),
                fg_color=OBS["surface2"],
                hover_color=OBS["purple"],
                command=lambda t=text: self._save_ai_response_to_vault(t),
            ).pack(side="right")

        ctk.CTkLabel(
            card,
            text=text,
            font=ctk.CTkFont(size=12),
            text_color=OBS["text"],
            wraplength=650,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(4, 10))

        self.after(60, lambda: self._chat_stream._parent_canvas.yview_moveto(1.0))

    def _save_ai_response_to_vault(self, content: str):
        title = f"AI Insight {datetime.now().strftime('%Y-%m-%d %H%M')}"
        note = self.vault.save_note(
            title=title,
            content=f"# {title}\n\n{content}\n\n#jarvis #ai-conversation\n",
            folder="AI-Conversations",
        )
        self._refresh_file_tree()
        self._open_note(note)

    def _append_typing(self) -> str:
        uid = f"typing_{int(time.time() * 1000)}"
        outer = ctk.CTkFrame(self._chat_stream, fg_color="transparent")
        outer.pack(fill="x", padx=12, pady=4, anchor="w")
        outer._uid = uid  # type: ignore[attr-defined]

        card = ctk.CTkFrame(outer, fg_color=OBS["surface"], corner_radius=12, border_width=1, border_color=OBS["purple"])
        card.pack(anchor="w")
        ctk.CTkLabel(card, text="JARVIS", font=ctk.CTkFont(size=10, weight="bold"), text_color=OBS["lavender"]).pack(anchor="w", padx=14, pady=(8, 0))
        ctk.CTkLabel(card, text="· · ·", font=ctk.CTkFont(size=15), text_color=OBS["purple_mid"]).pack(anchor="w", padx=14, pady=(2, 8))
        self.after(60, lambda: self._chat_stream._parent_canvas.yview_moveto(1.0))
        return uid

    def _remove_typing(self, uid: str):
        for widget in self._chat_stream.winfo_children():
            if getattr(widget, "_uid", None) == uid:
                widget.destroy()
                break

    def _on_send(self):
        text = self._chat_entry.get().strip()
        if not text:
            return
        self._chat_entry.delete(0, "end")
        self._send_async(text)

    def _send_async(self, command: str):
        self._append_msg("You", command)
        self._btn_send.configure(state="disabled", text="···")
        uid = self._append_typing()

        def worker():
            try:
                resp = self.brain.process(command)
                reply = resp.text or "(no response)"
            except Exception as exc:
                reply = f"Error: {exc}"
            self.after(0, lambda: self._finish_send(uid, reply))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_send(self, uid: str, reply: str):
        self._remove_typing(uid)
        self._append_msg("JARVIS", reply)
        self._btn_send.configure(state="normal", text="Send  ›")
        self._refresh_file_tree()

    # ── 4. TASK MATRIX VIEW ───────────────────────────────────────────────────

    def _build_tasks_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=OBS["bg"], corner_radius=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="📋  Task & Action Matrix (Obsidian Synced)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(side="left", padx=16)

        # Add Task Bar
        add_row = ctk.CTkFrame(frame, fg_color=OBS["surface2"], corner_radius=0, height=48)
        add_row.grid(row=1, column=0, sticky="ew")
        add_row.grid_columnconfigure(0, weight=1)
        add_row.grid_propagate(False)

        self._task_entry = ctk.CTkEntry(
            add_row,
            placeholder_text="New action item…",
            height=32,
            corner_radius=6,
            fg_color=OBS["surface"],
            border_color=OBS["border"],
            text_color=OBS["text"],
            font=ctk.CTkFont(size=11),
        )
        self._task_entry.grid(row=0, column=0, padx=(12, 6), pady=8, sticky="ew")
        self._task_entry.bind("<Return>", lambda _: self._add_task())

        self._due_entry = ctk.CTkEntry(
            add_row,
            placeholder_text="Due (e.g. today, friday)",
            width=150,
            height=32,
            corner_radius=6,
            fg_color=OBS["surface"],
            border_color=OBS["border"],
            text_color=OBS["text"],
            font=ctk.CTkFont(size=11),
        )
        self._due_entry.grid(row=0, column=1, padx=4, pady=8)

        ctk.CTkButton(
            add_row,
            text="+ Add Task",
            width=90,
            height=32,
            corner_radius=6,
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._add_task,
        ).grid(row=0, column=2, padx=(4, 12), pady=8)

        # Task List
        self._task_list = ctk.CTkScrollableFrame(
            frame,
            fg_color=OBS["bg"],
            scrollbar_button_color=OBS["purple"],
        )
        self._task_list.grid(row=2, column=0, sticky="nsew")
        self._refresh_tasks()
        return frame

    def _refresh_tasks(self):
        for w in self._task_list.winfo_children():
            w.destroy()
        store = TaskStore(self.settings.db_path)
        tasks = store.all(include_done=True)
        if not tasks:
            ctk.CTkLabel(
                self._task_list,
                text="No action items. Add one above or via chat: 'task buy groceries'",
                text_color=OBS["text_dim"],
                font=ctk.CTkFont(size=12),
            ).pack(pady=30)
            return

        for t in tasks:
            card = ctk.CTkFrame(
                self._task_list,
                fg_color=OBS["surface"],
                corner_radius=8,
                border_width=1,
                border_color=OBS["border"] if not t.done else OBS["surface2"],
            )
            card.pack(fill="x", padx=14, pady=4)
            card.grid_columnconfigure(0, weight=1)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.grid(row=0, column=0, sticky="ew", padx=12, pady=8)

            ctk.CTkLabel(
                left,
                text=f"{'✓ ' if t.done else '○ '}{t.text}",
                font=ctk.CTkFont(size=12, overstrike=t.done),
                text_color=OBS["text_dim"] if t.done else OBS["text"],
                anchor="w",
            ).pack(anchor="w")

            if t.due:
                ctk.CTkLabel(
                    left,
                    text=f"⏰  Due: {t.due}",
                    font=ctk.CTkFont(size=10),
                    text_color=OBS["amber"],
                ).pack(anchor="w")

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, padx=(0, 10), pady=6, sticky="e")

            ctk.CTkButton(
                btn_frame,
                text="↺ Undo" if t.done else "✓ Done",
                width=65,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                fg_color=OBS["surface2"],
                hover_color=OBS["purple"],
                command=lambda tid=t.id: self._toggle_task(tid),
            ).pack(side="left", padx=3)

            ctk.CTkButton(
                btn_frame,
                text="✕",
                width=26,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                fg_color=OBS["surface2"],
                hover_color=OBS["red"],
                command=lambda tid=t.id: self._delete_task(tid),
            ).pack(side="left")

    def _add_task(self):
        text = self._task_entry.get().strip()
        due  = self._due_entry.get().strip() or None
        if not text:
            return
        TaskStore(self.settings.db_path).add(text, due=due)
        self._task_entry.delete(0, "end")
        self._due_entry.delete(0, "end")
        self._refresh_tasks()

    def _toggle_task(self, tid: int):
        store = TaskStore(self.settings.db_path)
        from contextlib import closing
        from memory.store import connect
        with closing(connect(store.path)) as conn:
            row = conn.execute("SELECT done FROM tasks WHERE id=?", (tid,)).fetchone()
            if row:
                conn.execute("UPDATE tasks SET done=? WHERE id=?", (0 if row["done"] else 1, tid))
                conn.commit()
        self._refresh_tasks()

    def _delete_task(self, tid: int):
        TaskStore(self.settings.db_path).delete(tid)
        self._refresh_tasks()

    # ── 5. CODING AGENT VIEW ──────────────────────────────────────────────────

    def _build_agent_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color=OBS["bg"], corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="🤖  Claude Code Autonomous Agent Launcher",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(side="left", padx=16)

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=30, pady=30)
        body.grid_columnconfigure(0, weight=1)

        desc = ctk.CTkFrame(body, fg_color=OBS["surface"], corner_radius=12, border_width=1, border_color=OBS["purple"])
        desc.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(
            desc,
            text="⬡  Terminal Agent Connected to JARVIS Vault",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(anchor="w", padx=20, pady=(18, 4))

        ctk.CTkLabel(
            desc,
            text="Launch an autonomous Claude Code agent terminal with full access to this project and your Obsidian notes.\nUses your selected OmniRoute AI profile.",
            font=ctk.CTkFont(size=12),
            text_color=OBS["text_dim"],
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 18))

        ctk.CTkButton(
            body,
            text="🚀  Launch Claude Code (auto-best-free)",
            height=48,
            corner_radius=10,
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._launch_claude("auto-best-free"),
        ).grid(row=1, column=0, sticky="ew", pady=6)

        ctk.CTkButton(
            body,
            text=f"⚡  Launch with Active Profile: {self.current_model}",
            height=48,
            corner_radius=10,
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            border_width=1,
            border_color=OBS["purple"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._launch_claude(self.current_model),
        ).grid(row=2, column=0, sticky="ew", pady=6)

        return frame

    def _launch_claude(self, profile: str):
        target_dir = str(Path(self.settings.db_path).parent)
        claude_exe  = get_claude_executable()
        profile_dir = os.path.expanduser(f"~/.claude/profiles/{profile}")
        ps = (
            f"$Host.UI.RawUI.WindowTitle='Claude [{profile}]';"
            f"$env:CLAUDE_CONFIG_DIR='{profile_dir}';"
            f"$env:ANTHROPIC_BASE_URL='http://localhost:20128';"
            f"$env:ANTHROPIC_AUTH_TOKEN='dummy';"
            "Remove-Item env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue;"
            f"Set-Location '{target_dir}';"
            f"& '{claude_exe}'"
        )
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "powershell", "-NoExit", "-Command", ps],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            self._append_msg("System", f"Claude Code launched → profile `{profile}`")
        except Exception as exc:
            self._append_msg("System", f"Launch failed: {exc}")
        self.select_view("chat")

    # ── 6. ROBUST SETTINGS VIEW ───────────────────────────────────────────────

    def _build_settings_view(self) -> ctk.CTkFrame:
        from tkinter import filedialog, messagebox

        frame = ctk.CTkFrame(self, fg_color=OBS["bg"], corner_radius=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Header Bar with Save & Toast
        header = ctk.CTkFrame(frame, fg_color=OBS["surface"], corner_radius=0, height=50)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="⚙️  JARVIS & Obsidian System Configuration",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(side="left", padx=16)

        self._settings_toast = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=OBS["green"],
        )
        self._settings_toast.pack(side="left", padx=12)

        ctk.CTkButton(
            header,
            text="💾  Save & Apply Settings",
            width=160,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            command=self._save_settings_form,
        ).pack(side="right", padx=16)

        # Scrollable Settings Form
        scroll = ctk.CTkScrollableFrame(
            frame,
            fg_color=OBS["bg"],
            scrollbar_button_color=OBS["purple"],
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        scroll.grid_columnconfigure(0, weight=1)

        # ── CARD 1: 🤖 AI & OmniRoute Gateway ─────────────────────────────────
        c1 = ctk.CTkFrame(scroll, fg_color=OBS["surface"], corner_radius=12, border_width=1, border_color=OBS["border"])
        c1.pack(fill="x", pady=8, padx=4)
        c1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            c1,
            text="🤖  AI Model & OmniRoute Gateway",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        # AI Provider
        ctk.CTkLabel(c1, text="AI Provider:", font=ctk.CTkFont(size=11), text_color=OBS["text_dim"]).grid(row=1, column=0, sticky="w", padx=16, pady=4)
        self._st_provider_var = ctk.StringVar(value=self.settings.ai_provider)
        ctk.CTkOptionMenu(
            c1,
            variable=self._st_provider_var,
            values=["omniroute", "ollama", "openai", "none"],
            height=28,
            fg_color=OBS["surface2"],
            button_color=OBS["purple"],
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=1, sticky="w", padx=16, pady=4)

        # AI Profile / Model
        ctk.CTkLabel(c1, text="Active Model Profile:", font=ctk.CTkFont(size=11), text_color=OBS["text_dim"]).grid(row=2, column=0, sticky="w", padx=16, pady=4)
        self._st_model_var = ctk.StringVar(value=self.current_model)
        ctk.CTkOptionMenu(
            c1,
            variable=self._st_model_var,
            values=self.available_models,
            height=28,
            fg_color=OBS["surface2"],
            button_color=OBS["purple"],
            font=ctk.CTkFont(size=11),
        ).grid(row=2, column=1, sticky="ew", padx=16, pady=4)

        # Gateway Endpoint URL
        ctk.CTkLabel(c1, text="OmniRoute Endpoint:", font=ctk.CTkFont(size=11), text_color=OBS["text_dim"]).grid(row=3, column=0, sticky="w", padx=16, pady=4)
        self._st_host_entry = ctk.CTkEntry(
            c1,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OBS["surface2"],
            border_color=OBS["border"],
            text_color=OBS["text"],
        )
        self._st_host_entry.insert(0, self.settings.omniroute_host)
        self._st_host_entry.grid(row=3, column=1, sticky="ew", padx=16, pady=4)

        # Timeout (seconds)
        ctk.CTkLabel(c1, text="Request Timeout (s):", font=ctk.CTkFont(size=11), text_color=OBS["text_dim"]).grid(row=4, column=0, sticky="w", padx=16, pady=4)
        self._st_timeout_entry = ctk.CTkEntry(
            c1,
            width=100,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OBS["surface2"],
            border_color=OBS["border"],
            text_color=OBS["text"],
        )
        self._st_timeout_entry.insert(0, str(int(self.settings.ai_timeout)))
        self._st_timeout_entry.grid(row=4, column=1, sticky="w", padx=16, pady=4)

        # Auto-start switch & Test Connection Button
        act_row = ctk.CTkFrame(c1, fg_color="transparent")
        act_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 16))

        self._st_autostart_var = ctk.BooleanVar(value=self.settings.omniroute_auto_start)
        ctk.CTkSwitch(
            act_row,
            text="Auto-start OmniRoute daemon on app launch",
            variable=self._st_autostart_var,
            font=ctk.CTkFont(size=11),
            text_color=OBS["text"],
            progress_color=OBS["purple"],
        ).pack(side="left")

        ctk.CTkButton(
            act_row,
            text="⚡ Ping & Test Connection",
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=self._test_ai_connection_ping,
        ).pack(side="right", padx=4)

        self._st_ping_result_lbl = ctk.CTkLabel(c1, text="", font=ctk.CTkFont(size=10))
        self._st_ping_result_lbl.grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 8))

        # ── CARD 2: 📂 Obsidian Knowledge Vault & PC Indexer ─────────────────
        c2 = ctk.CTkFrame(scroll, fg_color=OBS["surface"], corner_radius=12, border_width=1, border_color=OBS["border"])
        c2.pack(fill="x", pady=8, padx=4)
        c2.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            c2,
            text="📂  Obsidian Knowledge Base & PC Vault",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        # Vault Path
        ctk.CTkLabel(c2, text="Vault Location:", font=ctk.CTkFont(size=11), text_color=OBS["text_dim"]).grid(row=1, column=0, sticky="w", padx=16, pady=4)
        path_box = ctk.CTkFrame(c2, fg_color="transparent")
        path_box.grid(row=1, column=1, sticky="ew", padx=16, pady=4)
        path_box.grid_columnconfigure(0, weight=1)

        self._st_vault_entry = ctk.CTkEntry(
            path_box,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OBS["surface2"],
            border_color=OBS["border"],
            text_color=OBS["text"],
        )
        self._st_vault_entry.insert(0, str(self.vault.vault_path))
        self._st_vault_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            path_box,
            text="Browse...",
            width=70,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=self._browse_vault_path,
        ).grid(row=0, column=1, padx=2)

        ctk.CTkButton(
            path_box,
            text="Default",
            width=65,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=lambda: (self._st_vault_entry.delete(0, "end"), self._st_vault_entry.insert(0, str(PROJECT_ROOT / "vault"))),
        ).grid(row=0, column=2, padx=2)

        # Vault Quick Actions
        v_act = ctk.CTkFrame(c2, fg_color="transparent")
        v_act.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 16))

        ctk.CTkButton(
            v_act,
            text="🔄 Scan & Index Drives A: and C:",
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OBS["purple"],
            hover_color=OBS["purple_mid"],
            command=self._rescan_pc_and_refresh,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            v_act,
            text="🚀 Open in Obsidian App",
            height=30,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=lambda: self.vault.open_in_obsidian(),
        ).pack(side="left", padx=4)

        # ── CARD 3: 💬 AI System Prompt & Personality ─────────────────────────
        c3 = ctk.CTkFrame(scroll, fg_color=OBS["surface"], corner_radius=12, border_width=1, border_color=OBS["border"])
        c3.pack(fill="x", pady=8, padx=4)
        c3.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            c3,
            text="💬  Custom AI Personality & Instructions",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            c3,
            text="Set the baseline system prompt used for all JARVIS conversational reasoning and Obsidian knowledge actions.",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self._st_prompt_box = ctk.CTkTextbox(
            c3,
            height=80,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=OBS["surface2"],
            text_color=OBS["text"],
            border_width=1,
            border_color=OBS["border"],
            corner_radius=8,
        )
        self._st_prompt_box.insert("1.0", self.settings.system_prompt)
        self._st_prompt_box.pack(fill="x", padx=16, pady=(0, 14))

        # ── CARD 4: 🛠️ Database, Diagnostics & Maintenance ────────────────────
        c4 = ctk.CTkFrame(scroll, fg_color=OBS["surface"], corner_radius=12, border_width=1, border_color=OBS["border"])
        c4.pack(fill="x", pady=8, padx=4)
        c4.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            c4,
            text="🛠️  System Maintenance & Diagnostics",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OBS["lavender"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        # Stats info
        db_path = Path(self.settings.db_path)
        db_size_kb = round(db_path.stat().st_size / 1024.0, 1) if db_path.exists() else 0
        total_notes = len(self.vault.list_notes())

        stats_text = (
            f"• Database: {db_path.name} ({db_size_kb} KB)\n"
            f"• Obsidian Vault Notes: {total_notes} documents\n"
            f"• CPU Telemetry: {'Active' if psutil else 'psutil missing'}"
        )
        ctk.CTkLabel(c4, text=stats_text, font=ctk.CTkFont(size=11), text_color=OBS["text_dim"], justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=4)

        # Maintenance Buttons
        m_act = ctk.CTkFrame(c4, fg_color="transparent")
        m_act.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 14))

        ctk.CTkButton(
            m_act,
            text="🧹 Vacuum SQLite DB",
            width=130,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["purple"],
            command=self._vacuum_database,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            m_act,
            text="🗑️ Clear Chat History",
            width=130,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=10),
            fg_color=OBS["surface2"],
            hover_color=OBS["red"],
            command=self._clear_chat_stream,
        ).pack(side="left", padx=4)

        return frame

    def _browse_vault_path(self):
        from tkinter import filedialog
        chosen = filedialog.askdirectory(initialdir=str(self.vault.vault_path), title="Select Obsidian Vault Directory")
        if chosen:
            self._st_vault_entry.delete(0, "end")
            self._st_vault_entry.insert(0, str(chosen))

    def _test_ai_connection_ping(self):
        self._st_ping_result_lbl.configure(text="⏳ Pinging OmniRoute gateway...", text_color=OBS["amber"])

        def ping_worker():
            host = self._st_host_entry.get().strip() or self.settings.omniroute_host
            model = self._st_model_var.get().strip()
            url = f"{host.rstrip('/')}/chat/completions"
            import urllib.request, json
            t0 = time.time()
            try:
                from skills.ai_skill import _post_json, _normalize_omniroute_model
                payload = {
                    "model": _normalize_omniroute_model(model),
                    "messages": [{"role": "user", "content": "ping"}],
                    "stream": False,
                }
                res = _post_json(url, payload, {"Authorization": "Bearer dummy"}, timeout=12.0)
                latency = int((time.time() - t0) * 1000)
                lat = latency
                mod_name = model
                rep_snippet = reply
                self.after(0, lambda l=lat, m=mod_name, r=rep_snippet: self._st_ping_result_lbl.configure(
                    text=f"🟢 Connected! HTTP 200 ({l}ms) — Model: {m} — Reply: \"{r}...\"",
                    text_color=OBS["green"],
                ))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda err=err_msg: self._st_ping_result_lbl.configure(
                    text=f"🔴 Ping Failed: {err}",
                    text_color=OBS["red"],
                ))

        threading.Thread(target=ping_worker, daemon=True).start()

    def _save_settings_form(self):
        # 1. Update environment variables
        prov = self._st_provider_var.get().strip()
        mod  = self._st_model_var.get().strip()
        host = self._st_host_entry.get().strip()
        tout = self._st_timeout_entry.get().strip() or "60"
        vpath = self._st_vault_entry.get().strip()
        prompt = self._st_prompt_box.get("1.0", "end-1c").strip()
        autostart = str(self._st_autostart_var.get()).lower()

        os.environ["JARVIS_AI_PROVIDER"] = prov
        os.environ["JARVIS_OMNIROUTE_MODEL"] = mod
        os.environ["JARVIS_OMNIROUTE_HOST"] = host
        os.environ["JARVIS_AI_TIMEOUT"] = tout
        os.environ["JARVIS_VAULT_PATH"] = vpath
        os.environ["JARVIS_SYSTEM_PROMPT"] = prompt
        os.environ["JARVIS_OMNIROUTE_AUTO_START"] = autostart

        # 2. Persist in PrefStore
        from memory.prefs import PrefStore
        prefs = PrefStore(self.settings.db_path)
        prefs.set("ai_provider", prov)
        prefs.set("omniroute_model", mod)
        prefs.set("omniroute_host", host)
        prefs.set("ai_timeout", tout)
        prefs.set("vault_path", vpath)
        prefs.set("system_prompt", prompt)

        # 3. Reload settings and recreate Brain
        self.settings = Settings.from_env()
        self.brain = build_brain(self.settings)
        self.vault = VaultManager(self.settings.vault_path)
        self.current_model = mod

        # 4. Refresh UI indicators
        if hasattr(self, "_model_var"):
            self._model_var.set(mod)
        if hasattr(self, "_sb_model"):
            self._sb_model.configure(text=f"⚡ {mod}")
        if hasattr(self, "_sb_vault"):
            self._sb_vault.configure(text=f"📁 Vault: {self.vault.vault_path.name}")

        self._refresh_file_tree()
        if hasattr(self, "_graph_canvas"):
            self._graph_canvas.set_graph_data(self.vault.get_graph_data(), self._omni_online)

        # 5. Show toast
        self._settings_toast.configure(text="✅ Settings saved & applied successfully!")
        self.after(4000, lambda: self._settings_toast.configure(text=""))

    def _vacuum_database(self):
        from contextlib import closing
        from memory.store import connect
        with closing(connect(self.settings.db_path)) as conn:
            conn.execute("VACUUM")
        self._settings_toast.configure(text="✅ Database optimized and compacted!")
        self.after(3000, lambda: self._settings_toast.configure(text=""))

    def _clear_chat_stream(self):
        for w in self._chat_stream.winfo_children():
            w.destroy()
        self._append_msg("JARVIS", "Chat stream cleared. Ready for new conversation.")

    # ── 6. BOTTOM OBSIDIAN STATUS BAR ─────────────────────────────────────────

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, height=26, fg_color=OBS["sidebar"], corner_radius=0)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)

        # Left status indicators
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=12)

        self._sb_vault = ctk.CTkLabel(
            left,
            text=f"📁 Vault: {self.vault.vault_path.name}",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        )
        self._sb_vault.pack(side="left", padx=6)

        self._sb_words = ctk.CTkLabel(
            left,
            text="0 words",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        )
        self._sb_words.pack(side="left", padx=6)

        self._sb_chars = ctk.CTkLabel(
            left,
            text="0 chars",
            font=ctk.CTkFont(size=10),
            text_color=OBS["text_dim"],
        )
        self._sb_chars.pack(side="left", padx=6)

        # Right status indicators
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=12)

        self._sb_model = ctk.CTkLabel(
            right,
            text=f"⚡ {self.current_model}",
            font=ctk.CTkFont(size=10),
            text_color=OBS["lavender"],
        )
        self._sb_model.pack(side="right", padx=6)

        self._sb_status = ctk.CTkLabel(
            right,
            text="● Online" if self._omni_online else "○ Offline",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=OBS["green"] if self._omni_online else OBS["red"],
        )
        self._sb_status.pack(side="right", padx=6)

    # ── NAVIGATION & TELEMETRY ────────────────────────────────────────────────

    def select_view(self, view_id: str):
        self._active_view = view_id
        for vid, view in self._views.items():
            if vid == view_id:
                view.grid()
            else:
                view.grid_remove()

        # Update top tab button highlights
        for vid, btn in self._top_tabs.items():
            btn.configure(
                fg_color=OBS["purple"] if vid == view_id else "transparent",
                text_color=OBS["text"] if vid == view_id else OBS["text_dim"],
            )

        if view_id == "graph":
            self._refresh_graph_view()
        elif view_id == "tasks":
            self._refresh_tasks()
        elif view_id == "editor":
            self._update_editor_stats()

    def _on_model_change(self, choice: str):
        self.current_model = choice
        os.environ["JARVIS_OMNIROUTE_MODEL"] = choice
        self.settings = Settings.from_env()
        self.brain    = build_brain(self.settings)
        if hasattr(self, "_sb_model"):
            self._sb_model.configure(text=f"⚡ {choice}")
        self._append_msg("System", f"Switched AI profile → `{choice}`")

    def _start_telemetry(self):
        def loop():
            while True:
                online = is_omniroute_online()
                cpu = ram = None
                if psutil:
                    try:
                        cpu = round(psutil.cpu_percent(), 1)
                        ram = round(psutil.virtual_memory().percent, 1)
                    except Exception:
                        pass
                self.after(0, lambda o=online, c=cpu, r=ram: self._update_telemetry(o, c, r))
                time.sleep(2.5)

        threading.Thread(target=loop, daemon=True).start()

    def _update_telemetry(self, online: bool, cpu: Optional[float], ram: Optional[float]):
        self._omni_online = online
        col = OBS["green"] if online else OBS["red"]
        self._omni_dot.delete("all")
        self._omni_dot.create_oval(1, 1, 7, 7, fill=col, outline="")
        self._omni_label.configure(
            text="OmniRoute Online" if online else "OmniRoute Offline",
            text_color=col,
        )

        if hasattr(self, "_sb_status"):
            self._sb_status.configure(
                text="● Online" if online else "○ Offline",
                text_color=col,
            )

        if cpu is not None:
            self._lbl_cpu.configure(text=f"CPU: {cpu}%")
        if ram is not None:
            self._lbl_ram.configure(text=f"RAM: {ram}%")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def launch_native_app():
    app = JarvisNativeApp()
    app.mainloop()


if __name__ == "__main__":
    launch_native_app()
