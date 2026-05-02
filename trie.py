"""
trie.py  —  Trie (Prefix Tree) Engine
=======================================
The single algorithm powering every game mechanic in CodeBreaker.

Three specialised Trie variants are built on one base:
  • CommandTrie  – shell command lookup & autocomplete
  • FileSystemTrie – the in-game directory tree (paths ARE prefixes)
  • LexiconTrie  – cipher-decode & intel-search word matching
"""

from __future__ import annotations
from typing import Generator


# ──────────────────────────────────────────────────────────────────────────────
# Core node
# ──────────────────────────────────────────────────────────────────────────────

class TrieNode:
    __slots__ = ("children", "is_end", "payload", "weight")

    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.is_end:   bool  = False
        self.payload:  object = None   # arbitrary metadata stored at end-nodes
        self.weight:   int   = 0       # for ranked suggestions (frequency)


# ──────────────────────────────────────────────────────────────────────────────
# Base Trie
# ──────────────────────────────────────────────────────────────────────────────

class Trie:
    """
    Generic Trie implementation.

    Complexity (m = key length, k = results returned, N = total keys):
      insert        O(m)
      search        O(m)
      starts_with   O(m)
      suggestions   O(m + k)   ← the key autocomplete win vs O(N·m) linear scan
      delete        O(m)
    Space: O(N · m) worst-case, O(N · σ) with shared prefixes (σ = alphabet size)
    """

    def __init__(self):
        self.root = TrieNode()
        self._size = 0

    # ── write ─────────────────────────────────────────────────────────

    def insert(self, key: str, payload=None, weight: int = 1) -> None:
        node = self.root
        for ch in key:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        if not node.is_end:
            self._size += 1
        node.is_end  = True
        node.payload = payload
        node.weight  = max(node.weight, weight)

    def delete(self, key: str) -> bool:
        """Remove a key. Returns True if it existed."""
        return self._delete(self.root, key, 0)

    def _delete(self, node: TrieNode, key: str, depth: int) -> bool:
        if depth == len(key):
            if not node.is_end:
                return False
            node.is_end = False
            self._size -= 1
            return True
        ch = key[depth]
        if ch not in node.children:
            return False
        self._delete(node.children[ch], key, depth + 1)
        return True

    # ── read ──────────────────────────────────────────────────────────

    def search(self, key: str) -> bool:
        node = self._walk(key)
        return node is not None and node.is_end

    def get_payload(self, key: str) -> object:
        node = self._walk(key)
        return node.payload if (node and node.is_end) else None

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None

    def suggestions(self, prefix: str, limit: int = 8) -> list[tuple[str, object]]:
        """
        Return up to `limit` (key, payload) pairs whose keys start with `prefix`.
        Sorted by weight descending, then alphabetically.
        Uses DFS from the prefix node — O(m + k).
        """
        node = self._walk(prefix)
        if node is None:
            return []
        results: list[tuple[int, str, object]] = []
        self._dfs(node, prefix, results, limit * 4)   # collect more, then rank
        results.sort(key=lambda x: (-x[0], x[1]))
        return [(k, p) for _, k, p in results[:limit]]

    def all_keys(self) -> list[str]:
        """Return every key in the trie (alphabetical)."""
        results: list[tuple[int, str, object]] = []
        self._dfs(self.root, "", results, limit=10_000)
        return [k for _, k, _ in results]

    def size(self) -> int:
        return self._size

    # ── prefix-scan generator (for large tries) ───────────────────────

    def prefix_scan(self, prefix: str) -> Generator[str, None, None]:
        node = self._walk(prefix)
        if node is None:
            return
        yield from self._gen_dfs(node, prefix)

    def _gen_dfs(self, node: TrieNode, cur: str) -> Generator[str, None, None]:
        if node.is_end:
            yield cur
        for ch in sorted(node.children):
            yield from self._gen_dfs(node.children[ch], cur + ch)

    # ── helpers ───────────────────────────────────────────────────────

    def _walk(self, key: str) -> TrieNode | None:
        node = self.root
        for ch in key:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def _dfs(self, node: TrieNode, cur: str, out: list, limit: int) -> None:
        if len(out) >= limit:
            return
        if node.is_end:
            out.append((node.weight, cur, node.payload))
        for ch in sorted(node.children):
            if len(out) >= limit:
                break
            self._dfs(node.children[ch], cur + ch, out, limit)


# ──────────────────────────────────────────────────────────────────────────────
# Specialised variants
# ──────────────────────────────────────────────────────────────────────────────

class CommandTrie(Trie):
    """
    Stores shell commands with their help text & handler references.
    Used for: tab-completion, validation, help generation.
    """

    def register(self, command: str, description: str, handler=None, weight: int = 1):
        self.insert(command, payload={"desc": description, "handler": handler}, weight=weight)

    def complete(self, partial: str) -> list[str]:
        return [k for k, _ in self.suggestions(partial, limit=6)]

    def get_description(self, command: str) -> str | None:
        p = self.get_payload(command)
        return p["desc"] if p else None

    def get_handler(self, command: str):
        p = self.get_payload(command)
        return p["handler"] if p else None


class FileSystemTrie(Trie):
    """
    Models a virtual file system.  Each key is a full path like
    '/sys/core/firewall.cfg'.  Separating on '/' gives directory structure.

    is_end=True  → file node
    is_end=False → directory node (intermediate)

    The path itself IS a Trie prefix — navigating the FS is prefix-walking.
    """

    def add_file(self, path: str, content: str = "", locked: bool = False):
        self.insert(path, payload={"content": content, "locked": locked, "type": "file"})

    def add_dir(self, path: str):
        """Mark a directory node explicitly (not strictly required but cleaner)."""
        node = self.root
        for ch in path:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        # directories are NOT end-nodes; they're just intermediate nodes
        node.payload = {"type": "dir"}

    def ls(self, dir_path: str) -> list[str]:
        """List immediate children of a directory path."""
        prefix = dir_path.rstrip("/") + "/"
        results = set()
        for full_path in self.prefix_scan(prefix):
            rest = full_path[len(prefix):]
            if rest:
                # immediate child = everything up to next '/'
                child = rest.split("/")[0]
                results.add(child)
        return sorted(results)

    def is_file(self, path: str) -> bool:
        p = self.get_payload(path)
        return p is not None and p.get("type") == "file"

    def is_locked(self, path: str) -> bool:
        p = self.get_payload(path)
        return p is not None and p.get("locked", False)

    def read_file(self, path: str) -> str | None:
        p = self.get_payload(path)
        return p["content"] if p and p.get("type") == "file" else None

    def unlock_file(self, path: str):
        node = self._walk(path)
        if node and node.payload:
            node.payload["locked"] = False

    def path_suggestions(self, partial: str) -> list[str]:
        return [k for k, _ in self.suggestions(partial, limit=8)]


class LexiconTrie(Trie):
    """
    Word dictionary for:
      • Cipher decoding  – find all valid words in a scrambled string
      • Intel search     – prefix-search across document keywords
    """

    def load_words(self, words: list[str]):
        for i, w in enumerate(words):
            self.insert(w.lower(), weight=len(w))   # longer words = higher weight

    def decode_fragments(self, scrambled: str, min_len: int = 3) -> list[str]:
        """
        Find all valid words that can be formed from consecutive characters
        in `scrambled` (substring matching via prefix scan).
        O(n * m) where n = len(scrambled), m = avg word length.
        """
        found = set()
        s = scrambled.lower()
        for start in range(len(s)):
            node = self.root
            for end in range(start, len(s)):
                ch = s[end]
                if ch not in node.children:
                    break
                node = node.children[ch]
                if node.is_end and (end - start + 1) >= min_len:
                    found.add(s[start:end + 1])
        return sorted(found, key=lambda w: -len(w))

    def intel_search(self, query: str, limit: int = 10) -> list[str]:
        """Prefix search across the lexicon — powers the intel terminal."""
        return [k for k, _ in self.suggestions(query.lower(), limit=limit)]
