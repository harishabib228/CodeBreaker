# ⬡ CodeBreaker — Trie-Powered Hacker Intrusion Game

> A full desktop game built on the **Trie (Prefix Tree)** data structure.
> Course project for *Analysis of Algorithms*.

![Python](https://img.shields.io/badge/Python-3.10+-00ff41?style=flat-square&logo=python)
![No Dependencies](https://img.shields.io/badge/dependencies-none-00ff41?style=flat-square)

---

## Quick Start

```bash
python main.py
```

**Requirements:** Python 3.10+ — zero pip installs, pure standard library.
Opens automatically in your browser as a full GUI application.

> On first run, allow the browser to open `http://127.0.0.1:7474`

---

## What is this?

You've breached **NEXUS-7**, a classified government mainframe.
Navigate a virtual filesystem, crack encrypted ciphers, decode intercepted signals,
and search a classified intelligence database — across 4 escalating missions.

The entire game is driven by three specialised **Trie** variants. The Trie isn't
decorative here — every core mechanic depends on it.

---

## Application Architecture

```
codebreaker/
├── main.py       ← Entry point: python main.py
├── server.py     ← Local HTTP server + JSON API (stdlib only)
├── engine.py     ← Game state, command handlers, mission logic
├── trie.py       ← Trie algorithm: base class + 3 variants
├── world.py      ← Game data: filesystem, commands, words, missions
└── index.html    ← Full GUI (HTML/CSS/JS, served by server.py)
```

**How it works:**

```
python main.py
     │
     ├── starts HTTPServer on localhost:7474
     ├── opens browser automatically
     │
     └── browser loads index.html
              │
              ├── user types command → POST /api/run
              ├── user presses TAB   → POST /api/tab  → CommandTrie / FileSystemTrie
              └── game renders response lines + updates sidebar
```

The browser is the rendering layer. Python is the application.
This is the same architecture used by VS Code, Jupyter, and many production desktop apps.

---

## The Algorithm: Trie (Prefix Tree)

### Node structure

```python
class TrieNode:
    children: dict[str, TrieNode]  # char → child node
    is_end:   bool                  # marks complete key
    payload:  object                # metadata (file content, help text…)
    weight:   int                   # for ranked suggestions
```

### Visual example — CommandTrie after inserting "cat", "cd", "crack", "clear", "scan"

```
root
 ├── c ─── a ─── t ✓         (cat)
 │    ├── d ✓                 (cd)
 │    ├── l ─── e ─── a ─── r ✓  (clear)
 │    └── r ─── a ─── c ─── k ✓  (crack)
 └── s ─── c ─── a ─── n ✓   (scan)
```

Typing `cr` → walk root→c→r, then DFS collects `crack`. **O(m + k)** regardless
of how many total commands exist.

### Complexity

| Operation | Trie | Sorted list | Hash map |
|---|---|---|---|
| insert | O(m) | O(m log n) | O(m) avg |
| exact search | O(m) | O(m log n) | O(m) avg |
| prefix exists? | O(m) | O(m log n) | ✗ not supported |
| **autocomplete** | **O(m + k)** | O(m log n + k) | ✗ not supported |
| prefix scan (generator) | O(m + k) lazy | O(n·m) eager | ✗ |
| substring decode | O(n·m) w/ early exit | O(n·m·w) | O(n·m·w) |

> m = key length, n = keys in trie, k = results returned, w = dictionary size

---

## Three Trie Variants

### 1. `CommandTrie` — shell autocomplete

```python
cmd_trie = CommandTrie()
cmd_trie.register("crack", "Crack a locked file", handler=fn)
cmd_trie.complete("cr")        # → ["crack"]
cmd_trie.get_handler("crack")  # → fn
```

Powers: TAB key, command validation, unknown-command suggestions, help text.

### 2. `FileSystemTrie` — the virtual filesystem IS a Trie

Every file path (`/intel/ops/targets.csv`) is a Trie key, stored character by character.
Directory listing = prefix scan on `"/intel/ops/"`. Navigation = walking the tree.

```python
fs = FileSystemTrie()
fs.add_file("/intel/ops/targets.csv", content="...", locked=False)
fs.ls("/intel/ops")              # → ["BLACKSITE.txt", "PHANTOM.txt", "targets.csv"]
fs.prefix_scan("/intel/")        # generator — powers 'scan' command O(k) lazy
fs.path_suggestions("/sys/a")    # → ["/sys/auth/keys.db", "/sys/auth/shadow", ...]
```

The insight: a filesystem already has hierarchical prefix structure.
Modelling it as a Trie makes all operations naturally O(m).

### 3. `LexiconTrie` — cipher decoding & intel search

```python
lex = LexiconTrie()
lex.load_words(CIPHER_WORDS)

lex.decode_fragments("FKCRACKTHESHADOW", min_len=4)
# → ["crack", "rack", "shadow", "hack", ...]
# Early exit: when no child exists, stops scanning — prunes dead branches

lex.intel_search("ph")
# → ["phantom"] — prefix DFS over the intel keyword trie
```

`decode_fragments` inner loop:
```python
for start in range(len(scrambled)):
    node = self.root
    for end in range(start, len(scrambled)):
        ch = scrambled[end]
        if ch not in node.children:
            break           # ← Trie prunes here — no hash lookup needed
        node = node.children[ch]
        if node.is_end:
            found.add(scrambled[start:end+1])
```

---

## Missions

| # | Title | Mechanics used |
|---|---|---|
| 1 | FIRST CONTACT | `ls`, `cd`, `cat` — FileSystemTrie navigation |
| 2 | DEEP SCAN | `scan` (prefix_scan), `crack` (LexiconTrie decode) |
| 3 | SIGNAL INTERCEPT | `decrypt` (decode_fragments), `search` (intel_search) |
| 4 | VAULT BREACH | `recover`, `override`, `exfil` — unlocked by completing prior missions |

---

## Presentation Guide (15–20 min)

**1. Algorithm first (5 min)**
- Open `trie.py`, show `TrieNode` — just a dict of children
- Walk through `insert()` and `suggestions()` live
- Draw the tree on the whiteboard for "cat/cd/crack/clear"
- Explain O(m+k) vs O(n·m) — *after walking to the prefix node, we only touch the k results, not all n keys*

**2. The three variants (3 min)**
- Show `FileSystemTrie.ls()` — "paths are already prefixes, the FS is naturally a Trie"
- Show `LexiconTrie.decode_fragments()` — point out the `break` (early exit = Trie pruning)

**3. Live demo (7 min)**
- `python main.py` — boot animation, browser opens
- Type `c` → watch the autocomplete sidebar populate and the Trie canvas highlight the `c` branch
- Run `ls /intel/ops` → `cat /intel/ops/targets.csv` → complete Mission 1
- Run `scan /sys/auth` → `crack` → show the puzzle overlay (LexiconTrie at work)
- Run `search phantom` → show intel results

**4. Architecture + GitHub (3 min)**
- Show commit history — algorithm built first, game wrapped around it
- Point out `server.py`: "Python stdlib HTTP server, no Flask, no Django"
- "Same pattern as VS Code's language server — Python does the logic, browser does the rendering"
