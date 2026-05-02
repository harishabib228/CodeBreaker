"""
world.py  —  CodeBreaker Game World
=====================================
All static game data: the virtual filesystem, command registry,
mission definitions, cipher words, and intel database.
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# Virtual Filesystem
# ──────────────────────────────────────────────────────────────────────────────

FILESYSTEM = {
    # path                          content                                      locked
    "/":                           ("Root directory of NEXUS-7 mainframe",      False),
    "/sys":                        ("System core directory",                     False),
    "/sys/kernel.bin":             ("NEXUS-7 kernel v4.2.1 [CLASSIFIED]",       True),
    "/sys/firewall.cfg":           ("ALLOW 10.0.0.1\nDENY *\nPORT 443 OPEN",   False),
    "/sys/auth":                   ("Authentication subsystem",                  False),
    "/sys/auth/shadow":            ("root:$6$hashed_password_data",              True),
    "/sys/auth/sessions.log":      ("SESSION 2024-01-15 root@10.0.0.1 ACTIVE",  False),
    "/sys/auth/keys.db":           ("RSA-4096 MASTER KEY: [ENCRYPTED BLOCK]",   True),
    "/intel":                      ("Intelligence archive",                       False),
    "/intel/ops":                  ("Active operations",                          False),
    "/intel/ops/BLACKSITE.txt":    ("BLACKSITE: coordinates 40.7128 N 74.0060 W",True),
    "/intel/ops/PHANTOM.txt":      ("PHANTOM protocol activated. Asset: ECHO-7", True),
    "/intel/ops/targets.csv":      ("ID,ALIAS,STATUS\n001,WRAITH,ACTIVE",        False),
    "/intel/archive":              ("Archived intel",                             False),
    "/intel/archive/2023_ops.tar": ("OPERATION DUSK: COMPLETED\nCANARY: BURNED", False),
    "/intel/archive/signals.log":  ("FREQ 147.250 MHz INTERCEPT: DELTA ZERO",   False),
    "/comms":                      ("Communications hub",                         False),
    "/comms/broadcast.cfg":        ("CHANNEL: SECURE-1\nENCRYPT: AES-256",       False),
    "/comms/intercepts":           ("Raw signal intercepts",                       False),
    "/comms/intercepts/raw_01.dat":("..-- --- .-. ... . -.-. --- -.. .",          False),
    "/comms/intercepts/raw_02.dat":("CIPHER: NEXUS PHANTOM WRAITH BLACKSITE",     True),
    "/vault":                      ("High-security vault",                         False),
    "/vault/MASTKEY.enc":          ("MASTER DECRYPTION KEY - REQUIRES LEVEL 5",  True),
    "/vault/mission_log.txt":      ("MISSION LOG CORRUPTED - USE RECOVER CMD",    True),
    "/vault/override.sh":          ("#!/bin/bash\n# SYSTEM OVERRIDE SCRIPT",      True),
}

DIRS = ["/", "/sys", "/sys/auth", "/intel", "/intel/ops",
        "/intel/archive", "/comms", "/comms/intercepts", "/vault"]

# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────

COMMANDS = {
    # command          description
    "help":           "List available commands",
    "ls":             "List directory contents        usage: ls [path]",
    "cd":             "Change directory               usage: cd <path>",
    "cat":            "Read a file                    usage: cat <path>",
    "pwd":            "Print working directory",
    "scan":           "Scan directory for locked files usage: scan [path]",
    "crack":          "Crack a locked file (uses cipher puzzle)",
    "decrypt":        "Decrypt an intercepted signal   usage: decrypt <path>",
    "search":         "Search intel database           usage: search <keyword>",
    "recover":        "Recover corrupted data          usage: recover <path>",
    "status":         "Show current mission status",
    "missions":       "List all missions",
    "clear":          "Clear terminal",
    "exit":           "Exit CodeBreaker",
    # hidden/unlockable
    "override":       "[CLASSIFIED] System override",
    "exfil":          "[CLASSIFIED] Exfiltrate data",
}

# ──────────────────────────────────────────────────────────────────────────────
# Cipher / Lexicon words  (used by LexiconTrie for decode puzzles)
# ──────────────────────────────────────────────────────────────────────────────

CIPHER_WORDS = [
    # common English words the cipher puzzles can hide
    "access", "admin", "agent", "alert", "alias",
    "black", "block", "break", "bridge", "bypass",
    "cache", "cipher", "clear", "clone", "code", "core", "crack",
    "data", "debug", "decrypt", "delta", "deploy", "detect",
    "echo", "encrypt", "error", "escape", "execute", "exploit",
    "false", "field", "firewall", "flag", "flash", "force",
    "ghost", "grant", "guard",
    "hack", "hash", "host",
    "inject", "intel",
    "key", "kill",
    "leak", "link", "lock", "login", "loop",
    "mask", "master", "match", "mirror", "mode",
    "nexus", "node", "null",
    "open", "ops", "origin", "override",
    "packet", "pass", "patch", "payload", "phantom", "ping", "port",
    "query", "queue",
    "relay", "remote", "reset", "root", "route",
    "scan", "secret", "secure", "shadow", "shell", "signal", "socket", "source",
    "target", "token", "trace", "track", "tunnel",
    "unlock", "upload", "user",
    "vault", "virus",
    "watch", "wraith",
    "zero", "zone",
]

# ──────────────────────────────────────────────────────────────────────────────
# Intel search database  (keyword → document snippet)
# ──────────────────────────────────────────────────────────────────────────────

INTEL_DB = {
    "blacksite":    "BLACKSITE: Codename for Project NEXUS offsite facility. Coordinates classified.",
    "phantom":      "PHANTOM: Active protocol. Involves asset ECHO-7. Authorization: DIRECTOR.",
    "wraith":       "WRAITH: Field operative. Status ACTIVE. Last contact: 72h ago.",
    "echo":         "ECHO-7: Deep cover asset. Identity classified beyond Level 4.",
    "nexus":        "NEXUS-7: Mainframe codename. Houses all DIRECTOR-level operations.",
    "director":     "DIRECTOR: Unknown identity. Communicated via PHANTOM channel only.",
    "override":     "OVERRIDE: Emergency system command. Requires vault key + root access.",
    "firewall":     "FIREWALL: NEXUS perimeter defense. Last updated 2024-01-10.",
    "shadow":       "SHADOW: Authentication bypass discovered in kernel v4.1.x. PATCHED.",
    "delta":        "DELTA ZERO: Evacuation codeword. Triggers wipe of /vault contents.",
    "signal":       "SIGNAL INTERCEPTS: Raw comms stored in /comms/intercepts/. Encrypted.",
    "key":          "MASTER KEY: Encrypted. Location: /vault/MASTKEY.enc. Requires Level 5.",
    "tunnel":       "TUNNEL: VPN route through NEXUS used by field operatives.",
    "target":       "TARGETS: Active target list in /intel/ops/targets.csv.",
    "asset":        "ASSETS: Registered assets logged in shadow directory.",
    "cipher":       "CIPHER: All comms use AES-256. Key rotation every 30 days.",
    "packet":       "PACKET LOGS: Available via scan command on /comms directory.",
    "zero":         "ZERO DAY: Known exploit in NEXUS auth module. Status: ACTIVE.",
    "ghost":        "GHOST PROTOCOL: Self-destruct sequence. DO NOT ACTIVATE.",
    "relay":        "RELAY: Signal relay station at /comms/broadcast.cfg.",
}

# ──────────────────────────────────────────────────────────────────────────────
# Missions
# ──────────────────────────────────────────────────────────────────────────────

MISSIONS = [
    {
        "id":    1,
        "title": "FIRST CONTACT",
        "brief": (
            "You've breached NEXUS-7's outer perimeter. Explore the filesystem, "
            "learn your tools, and locate the active operations directory."
        ),
        "objectives": [
            ("Read /sys/firewall.cfg",              "cat /sys/firewall.cfg"),
            ("List /intel/ops directory",           "ls /intel/ops"),
            ("Read the targets file",               "cat /intel/ops/targets.csv"),
        ],
        "reward":  "INTEL_ACCESS",
        "flavor":  "Connection established. NEXUS firewall neutralized.",
    },
    {
        "id":    2,
        "title": "DEEP SCAN",
        "brief": (
            "Locked files detected across the system. Run a full scan "
            "and crack the authentication shadow file."
        ),
        "objectives": [
            ("Scan /sys/auth for locked files",     "scan /sys/auth"),
            ("Crack the shadow file",               "crack"),
            ("Read the sessions log",               "cat /sys/auth/sessions.log"),
        ],
        "reward":  "AUTH_BYPASS",
        "flavor":  "Authentication layer compromised. Root access imminent.",
    },
    {
        "id":    3,
        "title": "SIGNAL INTERCEPT",
        "brief": (
            "COMMS traffic detected. Decrypt the intercepted signals "
            "and search the intel database for PHANTOM."
        ),
        "objectives": [
            ("Decrypt raw_01.dat",                  "decrypt /comms/intercepts/raw_01.dat"),
            ("Search intel for 'phantom'",          "search phantom"),
            ("Crack raw_02.dat cipher",             "crack"),
        ],
        "reward":  "COMMS_DECRYPTED",
        "flavor":  "PHANTOM protocol exposed. Asset ECHO-7 location narrowed.",
    },
    {
        "id":    4,
        "title": "VAULT BREACH",
        "brief": (
            "Final objective: breach the vault. Recover the mission log "
            "and exfiltrate the master key before NEXUS triggers DELTA ZERO."
        ),
        "objectives": [
            ("Recover /vault/mission_log.txt",      "recover /vault/mission_log.txt"),
            ("Search intel for 'override'",         "search override"),
            ("Use override command",                "override"),
        ],
        "reward":  "SYSTEM_COMPROMISED",
        "flavor":  "NEXUS-7 fully compromised. Mission complete. Vanish.",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Cipher puzzles  (used in 'crack' command)
# ──────────────────────────────────────────────────────────────────────────────
# Player sees scrambled string, must find hidden words using Trie prefix search.

CIPHER_PUZZLES = [
    {
        "scrambled": "FKCRACKTHESHADOWKX9",
        "hint":      "Find the word that means 'to break a code'",
        "answer":    "crack",
        "min_score": 1,
    },
    {
        "scrambled": "9XPHANTOMZERODELTAN",
        "hint":      "Find the active protocol name hidden in the noise",
        "answer":    "phantom",
        "min_score": 1,
    },
    {
        "scrambled": "OVERRIDEACCESSVAULT",
        "hint":      "Find the emergency system command",
        "answer":    "override",
        "min_score": 1,
    },
    {
        "scrambled": "XZWRAITHSIGNALECHO9",
        "hint":      "Find the field operative codename",
        "answer":    "wraith",
        "min_score": 1,
    },
]
