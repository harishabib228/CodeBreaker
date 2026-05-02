"""
engine.py  —  CodeBreaker Game Engine
=======================================
All game state and command handling logic, fully decoupled from the UI.
The UI (main.py) calls engine methods and renders what comes back.
"""

from __future__ import annotations
import random
import time

from trie import CommandTrie, FileSystemTrie, LexiconTrie
from world import (
    FILESYSTEM, DIRS, COMMANDS,
    CIPHER_WORDS, INTEL_DB, MISSIONS, CIPHER_PUZZLES,
)


# ──────────────────────────────────────────────────────────────────────────────
# Output tokens (drives UI colour)
# ──────────────────────────────────────────────────────────────────────────────

class Line:
    """A single output line with a style tag."""
    __slots__ = ("text", "style")
    NORMAL  = "normal"
    SUCCESS = "success"
    ERROR   = "error"
    WARN    = "warn"
    ACCENT  = "accent"
    DIM     = "dim"
    HEADER  = "header"
    DATA    = "data"

    def __init__(self, text: str, style: str = "normal"):
        self.text  = text
        self.style = style

    @staticmethod
    def ok(t):    return Line(t, Line.SUCCESS)
    @staticmethod
    def err(t):   return Line(t, Line.ERROR)
    @staticmethod
    def warn(t):  return Line(t, Line.WARN)
    @staticmethod
    def hi(t):    return Line(t, Line.ACCENT)
    @staticmethod
    def dim(t):   return Line(t, Line.DIM)
    @staticmethod
    def hdr(t):   return Line(t, Line.HEADER)
    @staticmethod
    def data(t):  return Line(t, Line.DATA)
    @staticmethod
    def nl():     return Line("", Line.NORMAL)


# ──────────────────────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────────────────────

class Engine:

    def __init__(self):
        # ── build tries ───────────────────────────────────────────────
        self.cmd_trie = CommandTrie()
        for cmd, desc in COMMANDS.items():
            self.cmd_trie.register(cmd, desc, weight=5 if cmd not in ("override","exfil") else 1)

        self.fs_trie = FileSystemTrie()
        for d in DIRS:
            self.fs_trie.add_dir(d)
        for path, (content, locked) in FILESYSTEM.items():
            if path not in DIRS:
                self.fs_trie.add_file(path, content, locked)

        self.lex_trie = LexiconTrie()
        self.lex_trie.load_words(CIPHER_WORDS)

        # ── game state ────────────────────────────────────────────────
        self.cwd              = "/"
        self.mission_idx      = 0
        self.completed_objs   : set[int] = set()   # indices of completed objectives
        self.unlocked_rewards : set[str] = set()
        self.score            = 0
        self.commands_run     = 0
        self.start_time       = time.time()
        self.current_puzzle   : dict | None = None
        self.puzzle_active    = False
        self.game_over        = False
        self.game_won         = False

        # ── objective tracking ────────────────────────────────────────
        # maps (mission_id, obj_idx) → bool
        self._obj_done: dict[tuple, bool] = {}

    # ── public API ────────────────────────────────────────────────────────────

    def current_mission(self) -> dict:
        if self.mission_idx < len(MISSIONS):
            return MISSIONS[self.mission_idx]
        return MISSIONS[-1]

    def tab_complete(self, partial: str) -> list[str]:
        """
        Smart tab completion using the CommandTrie and FileSystemTrie.
        If partial has a space, complete the argument (path).
        Otherwise complete the command.
        """
        parts = partial.split(" ", 1)
        if len(parts) == 1:
            return self.cmd_trie.complete(parts[0])
        else:
            cmd, arg = parts
            # path completion — always work with absolute paths internally
            path_partial = arg if arg.startswith("/") else self.cwd.rstrip("/") + "/" + arg
            matches = self.fs_trie.path_suggestions(path_partial)
            # Return full absolute paths (cleaner for the frontend to replace the arg)
            return matches

    def run(self, raw: str) -> list[Line]:
        """Parse and execute a command. Returns list of Line objects for display."""
        if self.puzzle_active:
            return self._handle_puzzle_input(raw)

        raw = raw.strip()
        if not raw:
            return []

        self.commands_run += 1
        parts = raw.split()
        cmd   = parts[0].lower()
        args  = parts[1:]

        # validate against CommandTrie
        if not self.cmd_trie.search(cmd):
            suggestions = self.cmd_trie.complete(cmd)
            out = [Line.err(f"Unknown command: '{cmd}'")]
            if suggestions:
                out.append(Line.dim(f"  Did you mean: {', '.join(suggestions[:3])}?"))
            out.append(Line.dim("  Type 'help' for command list."))
            return out

        # dispatch
        handlers = {
            "help":     self._cmd_help,
            "ls":       self._cmd_ls,
            "cd":       self._cmd_cd,
            "cat":      self._cmd_cat,
            "pwd":      self._cmd_pwd,
            "scan":     self._cmd_scan,
            "crack":    self._cmd_crack,
            "decrypt":  self._cmd_decrypt,
            "search":   self._cmd_search,
            "recover":  self._cmd_recover,
            "status":   self._cmd_status,
            "missions": self._cmd_missions,
            "clear":    lambda a: [Line("__CLEAR__")],
            "exit":     self._cmd_exit,
            "override": self._cmd_override,
            "exfil":    self._cmd_exfil,
        }
        result = handlers[cmd](args)
        self._check_objectives(raw)
        return result

    # ── command handlers ──────────────────────────────────────────────────────

    def _cmd_help(self, args) -> list[Line]:
        out = [
            Line.hdr("╔══════════════════════════════════════╗"),
            Line.hdr("║      NEXUS-7  COMMAND  REFERENCE      ║"),
            Line.hdr("╚══════════════════════════════════════╝"),
            Line.nl(),
        ]
        for cmd, desc in COMMANDS.items():
            if cmd in ("override", "exfil") and "AUTH_BYPASS" not in self.unlocked_rewards:
                continue
            out.append(Line(f"  {cmd:<12}  {desc}", Line.NORMAL))
        out += [
            Line.nl(),
            Line.dim("  [TAB] autocomplete  |  [↑↓] history  |  [ESC] cancel"),
        ]
        return out

    def _cmd_ls(self, args) -> list[Line]:
        path = self._resolve(args[0] if args else self.cwd)
        children = self.fs_trie.ls(path)
        if not children:
            # maybe it's a file
            if self.fs_trie.is_file(path):
                return [Line.warn(f"  {path}: is a file, not a directory")]
            return [Line.warn(f"  ls: no such directory: {path}")]

        out = [Line.hi(f"  Directory: {path}"), Line.nl()]
        for name in children:
            full = path.rstrip("/") + "/" + name
            if self.fs_trie.is_file(full):
                locked = self.fs_trie.is_locked(full)
                icon   = "🔒" if locked else "📄"
                style  = Line.WARN if locked else Line.NORMAL
                out.append(Line(f"  {icon}  {name}", style))
            else:
                out.append(Line(f"  📁  {name}/", Line.ACCENT))
        return out

    def _cmd_cd(self, args) -> list[Line]:
        if not args:
            self.cwd = "/"
            return [Line.ok("  Changed to /")]
        path = self._resolve(args[0])
        if path in DIRS or path == "/":
            self.cwd = path
            return [Line.ok(f"  Changed to {path}")]
        if self.fs_trie.is_file(path):
            return [Line.err(f"  cd: not a directory: {path}")]
        return [Line.err(f"  cd: no such directory: {path}")]

    def _cmd_cat(self, args) -> list[Line]:
        if not args:
            return [Line.err("  Usage: cat <path>")]
        path = self._resolve(args[0])
        if not self.fs_trie.is_file(path):
            return [Line.err(f"  cat: no such file: {path}")]
        if self.fs_trie.is_locked(path):
            return [
                Line.warn(f"  cat: {path}: PERMISSION DENIED [LOCKED]"),
                Line.dim("  Hint: use 'crack' to unlock locked files"),
            ]
        content = self.fs_trie.read_file(path)
        out = [Line.hi(f"  ── {path} ──"), Line.nl()]
        for l in content.splitlines():
            out.append(Line(f"  {l}", Line.DATA))
        return out

    def _cmd_pwd(self, args) -> list[Line]:
        return [Line.ok(f"  {self.cwd}")]

    def _cmd_scan(self, args) -> list[Line]:
        path = self._resolve(args[0] if args else self.cwd)
        out  = [Line.hi(f"  TRIE SCAN: {path}"), Line.nl(),
                Line.dim("  Walking prefix tree..."), Line.nl()]

        locked_found = []
        for full_path in self.fs_trie.prefix_scan(path.rstrip("/") + "/"):
            if self.fs_trie.is_locked(full_path):
                locked_found.append(full_path)

        if locked_found:
            out.append(Line.warn(f"  ⚠  {len(locked_found)} locked file(s) detected:"))
            for fp in locked_found:
                out.append(Line(f"     🔒 {fp}", Line.WARN))
        else:
            out.append(Line.ok("  ✓  No locked files found in this subtree"))

        out += [
            Line.nl(),
            Line.dim(f"  [TRIE] Prefix scan O(k) where k={len(locked_found)} matches"),
        ]
        return out

    def _cmd_crack(self, args) -> list[Line]:
        # Find a locked file to crack
        puzzle = self._get_next_puzzle()
        if not puzzle:
            return [Line.ok("  ✓ No locked targets remaining")]

        self.current_puzzle = puzzle
        self.puzzle_active  = True
        scrambled = puzzle["scrambled"]

        # Use LexiconTrie to pre-find all decodeable fragments (shown as hints)
        fragments = self.lex_trie.decode_fragments(scrambled, min_len=4)

        out = [
            Line.hdr("╔══════════════════════════════════════╗"),
            Line.hdr("║          CIPHER CRACK MODULE          ║"),
            Line.hdr("╚══════════════════════════════════════╝"),
            Line.nl(),
            Line.warn("  INTERCEPTED CIPHER STRING:"),
            Line.hi (f"  {scrambled}"),
            Line.nl(),
            Line.dim("  [TRIE] Scanning substrings for valid word prefixes..."),
            Line.nl(),
        ]
        if fragments:
            out.append(Line.ok(f"  TRIE found {len(fragments)} decodeable fragment(s):"))
            for f in fragments[:6]:
                out.append(Line(f"    • {f.upper()}", Line.DATA))
        out += [
            Line.nl(),
            Line.warn(f"  HINT: {puzzle['hint']}"),
            Line.nl(),
            Line.dim("  Type the correct word to crack the cipher ► "),
        ]
        return out

    def _handle_puzzle_input(self, raw: str) -> list[Line]:
        guess = raw.strip().lower()
        puzzle = self.current_puzzle

        if guess == puzzle["answer"]:
            self.puzzle_active = False
            self.current_puzzle = None
            self.score += 150
            # unlock the next locked file
            self._unlock_next_file()
            return [
                Line.nl(),
                Line.ok("  ✓  CIPHER CRACKED! Access granted."),
                Line.ok(f"  +150 points  |  Total: {self.score}"),
                Line.nl(),
                Line.dim("  Locked file unlocked. Use 'ls' or 'cat' to access."),
            ]
        else:
            # Give Trie-powered feedback: does their guess share a prefix?
            if self.lex_trie.starts_with(guess):
                hint = "Valid prefix — keep going"
            else:
                hint = "No match in lexicon trie"
            return [
                Line.err(f"  ✗  Incorrect: '{guess.upper()}'"),
                Line.dim(f"  [TRIE] {hint}"),
                Line.dim("  Try again ► "),
            ]

    def _cmd_decrypt(self, args) -> list[Line]:
        if not args:
            return [Line.err("  Usage: decrypt <path>")]
        path = self._resolve(args[0])
        content = self.fs_trie.read_file(path)
        if content is None:
            return [Line.err(f"  decrypt: no such file: {path}")]

        # Use LexiconTrie to find words in the signal
        found = self.lex_trie.decode_fragments(content, min_len=3)
        self.score += len(found) * 10

        out = [
            Line.hi(f"  ── DECRYPT: {path} ──"),
            Line.nl(),
            Line.data(f"  RAW:  {content[:60]}"),
            Line.nl(),
            Line.dim(f"  [TRIE] decode_fragments() found {len(found)} word(s):"),
            Line.nl(),
        ]
        if found:
            for w in found[:10]:
                out.append(Line(f"    ✓  {w.upper()}", Line.SUCCESS))
        else:
            out.append(Line.warn("  No recognisable words found in signal"))
        out += [Line.nl(), Line.ok(f"  +{len(found)*10} points decoded  |  Total: {self.score}")]
        return out

    def _cmd_search(self, args) -> list[Line]:
        if not args:
            return [Line.err("  Usage: search <keyword>")]
        query = args[0].lower()

        # Use LexiconTrie prefix search over INTEL_DB keys
        intel_trie = LexiconTrie()
        intel_trie.load_words(list(INTEL_DB.keys()))
        matches = intel_trie.intel_search(query, limit=8)

        out = [
            Line.hi(f"  ── INTEL SEARCH: '{query}' ──"),
            Line.dim(f"  [TRIE] prefix scan returned {len(matches)} match(es)"),
            Line.nl(),
        ]
        if matches:
            for key in matches:
                intel = INTEL_DB.get(key, "No data.")
                out.append(Line(f"  [{key.upper()}]", Line.ACCENT))
                out.append(Line(f"    {intel}", Line.DATA))
                out.append(Line.nl())
            self.score += len(matches) * 20
        else:
            out.append(Line.warn(f"  No intel found for query: '{query}'"))
        return out

    def _cmd_recover(self, args) -> list[Line]:
        if not args:
            return [Line.err("  Usage: recover <path>")]
        path = self._resolve(args[0])
        if not self.fs_trie.is_file(path):
            return [Line.err(f"  recover: no such file: {path}")]
        if self.fs_trie.is_locked(path):
            # unlock it via recover (mission mechanic)
            self.fs_trie.unlock_file(path)
            self.score += 200
            return [
                Line.ok(f"  ✓  RECOVERED: {path}"),
                Line.ok(f"  +200 points  |  Total: {self.score}"),
                Line.nl(),
                Line.data("  MISSION LOG RECOVERED:"),
                Line.data("  > OPERATION PHANTOM: Extract ECHO-7 from BLACKSITE"),
                Line.data("  > OVERRIDE CODE: DELTA-SEVEN-NEXUS"),
                Line.data("  > WARNING: DELTA ZERO triggers in 30 minutes of breach"),
            ]
        content = self.fs_trie.read_file(path)
        return [Line.warn("  File is not corrupted — use 'cat' to read it")]

    def _cmd_status(self, args) -> list[Line]:
        m   = self.current_mission()
        elapsed = int(time.time() - self.start_time)
        m_idx = self.mission_idx + 1
        out = [
            Line.hdr("╔══════════════════════════════════════╗"),
            Line.hdr(f"║  MISSION {m_idx}: {m['title']:<27}║"),
            Line.hdr("╚══════════════════════════════════════╝"),
            Line.nl(),
            Line.dim(f"  {m['brief']}"),
            Line.nl(),
            Line.hi ("  OBJECTIVES:"),
        ]
        for i, (desc, _) in enumerate(m["objectives"]):
            key  = (m["id"], i)
            done = self._obj_done.get(key, False)
            mark = "✓" if done else "○"
            col  = Line.SUCCESS if done else Line.NORMAL
            out.append(Line(f"    {mark}  {desc}", col))

        out += [
            Line.nl(),
            Line(f"  Score:    {self.score}", Line.ACCENT),
            Line(f"  Commands: {self.commands_run}", Line.DIM),
            Line(f"  Elapsed:  {elapsed}s", Line.DIM),
            Line.nl(),
            Line.dim(f"  Unlocked: {', '.join(self.unlocked_rewards) or 'none'}"),
        ]
        return out

    def _cmd_missions(self, args) -> list[Line]:
        out = [Line.hdr("  ── MISSION DOSSIER ──"), Line.nl()]
        for m in MISSIONS:
            done   = m["id"] <= self.mission_idx
            active = m["id"] == self.mission_idx + 1
            mark   = "✓" if done else ("►" if active else "○")
            style  = Line.SUCCESS if done else (Line.ACCENT if active else Line.DIM)
            out.append(Line(f"  {mark}  [{m['id']}] {m['title']}", style))
        return out

    def _cmd_exit(self, args) -> list[Line]:
        self.game_over = True
        return [
            Line.warn("  Closing connection..."),
            Line.dim("  Erasing traces..."),
            Line.ok ("  Connection terminated. Stay dark."),
        ]

    def _cmd_override(self, args) -> list[Line]:
        if "AUTH_BYPASS" not in self.unlocked_rewards:
            return [Line.err("  override: ACCESS DENIED — requires AUTH_BYPASS clearance")]
        self.score += 500
        self.unlocked_rewards.add("OVERRIDE_USED")
        return [
            Line.warn("  ⚠  SYSTEM OVERRIDE INITIATED"),
            Line.warn("  ⚠  NEXUS-7 SECURITY SUSPENDED"),
            Line.ok ("  ✓  All vault files unlocked"),
            Line.ok (f"  +500 points  |  Total: {self.score}"),
        ]

    def _cmd_exfil(self, args) -> list[Line]:
        if "OVERRIDE_USED" not in self.unlocked_rewards:
            return [Line.err("  exfil: vault must be overridden first")]
        self.game_won  = True
        self.game_over = True
        elapsed = int(time.time() - self.start_time)
        return [
            Line.nl(),
            Line.hdr("╔══════════════════════════════════════════╗"),
            Line.hdr("║          MISSION ACCOMPLISHED             ║"),
            Line.hdr("╚══════════════════════════════════════════╝"),
            Line.nl(),
            Line.ok("  NEXUS-7 fully compromised."),
            Line.ok("  All intelligence exfiltrated."),
            Line.nl(),
            Line(f"  Final Score:  {self.score}", Line.ACCENT),
            Line(f"  Time:         {elapsed}s", Line.ACCENT),
            Line(f"  Commands run: {self.commands_run}", Line.DIM),
            Line.nl(),
            Line.dim("  Press any key to return to terminal..."),
        ]

    # ── internals ─────────────────────────────────────────────────────────────

    def _resolve(self, path: str) -> str:
        """Resolve relative paths against cwd."""
        if path.startswith("/"):
            return path
        if path in ("..", "../"):
            parts = self.cwd.rstrip("/").split("/")
            return "/".join(parts[:-1]) or "/"
        return self.cwd.rstrip("/") + "/" + path

    def _check_objectives(self, raw_cmd: str):
        m = self.current_mission()
        all_done = True
        for i, (desc, trigger) in enumerate(m["objectives"]):
            key = (m["id"], i)
            if self._obj_done.get(key):
                continue
            if trigger.lower() in raw_cmd.lower() or raw_cmd.lower().startswith(trigger.split()[0].lower()):
                # loose match: command keyword present
                if raw_cmd.lower().startswith(trigger.split()[0]):
                    self._obj_done[key] = True
                    self.score += 100
            if not self._obj_done.get(key):
                all_done = False

        if all_done and self.mission_idx < len(MISSIONS) - 1:
            # advance mission
            reward = m["reward"]
            self.unlocked_rewards.add(reward)
            self.mission_idx += 1
            self.score += 300

    def _get_next_puzzle(self) -> dict | None:
        used = getattr(self, "_used_puzzles", set())
        for p in CIPHER_PUZZLES:
            if p["answer"] not in used:
                self._used_puzzles = used | {p["answer"]}
                return p
        return None

    def _unlock_next_file(self):
        """Unlock the first locked file we find, to reward the crack."""
        for path in self.fs_trie.all_keys():
            if self.fs_trie.is_locked(path):
                self.fs_trie.unlock_file(path)
                return
