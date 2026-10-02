#!/usr/bin/env python3
"""Shared helpers for the task-level receipts toolchain.

Used by wave-check.py, owns-check.py, findings-sync.py, task-accept.py.
Stdlib + PyYAML only. Nothing here calls the network.

Provenance: the ideas (owns_paths, acceptance receipt bound to hashes,
findings as canonical files) come from VKirill/claude-lane-stack @ e01145e (MIT).
The code is written from scratch for our work/{feature}/tasks/N.md layout.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterable

import yaml

FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n(.*)\Z", re.DOTALL)
DEFAULT_TIMEOUT_SEC = 900


# --------------------------------------------------------------------------- #
# Task files
# --------------------------------------------------------------------------- #

@dataclass
class Task:
    number: str
    path: Path
    frontmatter: dict[str, Any]
    body: str

    @property
    def wave(self) -> int:
        return int(self.frontmatter.get("wave") or 0)

    @property
    def status(self) -> str:
        return str(self.frontmatter.get("status") or "").strip()

    def list_field(self, name: str) -> list[str]:
        value = self.frontmatter.get(name)
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        return [str(v).strip() for v in value if str(v).strip()]

    @property
    def owns_paths(self) -> list[str]:
        return self.list_field("owns_paths")

    @property
    def reads(self) -> list[str]:
        return self.list_field("reads")

    @property
    def never_touch(self) -> list[str]:
        return self.list_field("never_touch")

    @property
    def depends_on(self) -> list[str]:
        return [str(d) for d in self.list_field("depends_on")]

    @property
    def body_sha256(self) -> str:
        """Hash of everything after the frontmatter block.

        Frontmatter changes legitimately during execution (status, start_commit);
        the body is the contract and must not change after the task started.
        """
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw, body = match.group(1), match.group(2)
    # Inline comments after values ("wave: 1   # волна") are valid YAML, but a
    # bare "teammate_name:" with a trailing comment yields None — fine.
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data, body


def load_task(path: Path) -> Task:
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    number = re.sub(r"\.md$", "", path.name)
    return Task(number=number, path=path, frontmatter=fm, body=body)


def load_tasks(feature_dir: Path) -> list[Task]:
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        raise FileNotFoundError(f"no tasks/ directory in {feature_dir}")
    tasks = [load_task(p) for p in tasks_dir.glob("*.md")]

    def sort_key(t: Task):
        return (0, int(t.number)) if t.number.isdigit() else (1, t.number)

    return sorted(tasks, key=sort_key)


def find_task(feature_dir: Path, number: str) -> Task:
    path = feature_dir / "tasks" / f"{number}.md"
    if not path.is_file():
        raise FileNotFoundError(f"task file not found: {path}")
    return load_task(path)


def task_log_dir(feature_dir: Path, number: str) -> Path:
    """Reviewer reports live here. NOTE: work/**/logs/working/ is gitignored."""
    return feature_dir / "logs" / "working" / f"task-{number}"


def task_receipts_dir(feature_dir: Path, number: str) -> Path:
    """Receipts (acceptance.json, owns-check.json, findings/, FINDINGS.md) live here.

    Deliberately outside logs/working/ so they are tracked by git — a receipt
    that is not in history is not evidence.
    """
    return feature_dir / "logs" / "receipts" / f"task-{number}"


# --------------------------------------------------------------------------- #
# Path ownership
# --------------------------------------------------------------------------- #

def norm_path(p: str) -> str:
    p = p.strip().replace("\\", "/")
    p = re.sub(r"^\./", "", p)
    return p.rstrip("/")


def _is_glob(p: str) -> bool:
    return any(ch in p for ch in "*?[")


def path_matches(path: str, pattern: str) -> bool:
    """True if `path` is inside `pattern` (a prefix directory, a file, or a glob)."""
    path, pattern = norm_path(path), norm_path(pattern)
    if _is_glob(pattern):
        if fnmatch(path, pattern):
            return True
        # "**/data/**" should also match "data/x"; fnmatch has no ** semantics,
        # so treat "**/" prefix as optional.
        if pattern.startswith("**/") and fnmatch(path, pattern[3:]):
            return True
        # "src/**" must match "src/a/b" but also "src/a"
        if pattern.endswith("/**") and (path == pattern[:-3] or path.startswith(pattern[:-3] + "/")):
            return True
        return False
    return path == pattern or path.startswith(pattern + "/")


def paths_overlap(a: str, b: str) -> bool:
    """Two ownership declarations overlap if either contains the other."""
    a, b = norm_path(a), norm_path(b)
    if _is_glob(a) or _is_glob(b):
        # Conservative: a glob overlaps anything it matches, and any glob whose
        # literal prefix contains / is contained in the other path.
        if _is_glob(a) and path_matches(b, a):
            return True
        if _is_glob(b) and path_matches(a, b):
            return True
        pa, pb = _glob_prefix(a), _glob_prefix(b)
        return bool(pa) and bool(pb) and (pa == pb or pa.startswith(pb + "/") or pb.startswith(pa + "/"))
    return path_matches(a, b) or path_matches(b, a)


def _glob_prefix(p: str) -> str:
    parts = []
    for seg in p.split("/"):
        if _is_glob(seg):
            break
        parts.append(seg)
    return "/".join(parts)


def owned_by(path: str, owns: Iterable[str]) -> bool:
    return any(path_matches(path, o) for o in owns)


# --------------------------------------------------------------------------- #
# Git
# --------------------------------------------------------------------------- #

def git(repo: Path, *args: str, check: bool = True) -> str:
    # core.quotepath=off: иначе git печатает не-ASCII пути в экранированном виде
    # ("\320\230..." в кавычках), и owns-check считает кириллический файл из
    # owns_paths утечкой (кириллическое имя документа в owns_paths задачи).
    result = subprocess.run(
        ["git", "-c", "core.quotepath=off", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=60,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def repo_root(start: Path) -> Path:
    return Path(git(start if start.is_dir() else start.parent, "rev-parse", "--show-toplevel").strip())


TASK_COMMIT_RE_TMPL = r"(?i)^(?:feat|fix|refactor|test|docs|perf|chore):\s.*\btask\s*{n}\b(?!\d)"  # без скоупа: chore(tasks): — коммиты ведущего, не задачи


def task_commits(repo: Path, start_commit: str, task_number: str | int) -> list[str]:
    """SHAs in start_commit..HEAD whose subject names this task (`task N`).

    The executor commit convention (`feat: task N — …`, `fix: address review round M
    for task N`) is what makes a commit attributable. A scoped type such as
    `chore(tasks): …` is the lead's bookkeeping and never counts, even if it names
    the task — it may carry whatever the shared index held at the time. In a checkout shared by several
    sessions, commits without the tag belong to someone else and must not count
    against this task's ownership.
    """
    pat = re.compile(TASK_COMMIT_RE_TMPL.format(n=int(task_number)))
    out = []
    for line in git(repo, "log", "--format=%H%x09%s", f"{start_commit}..HEAD").splitlines():
        sha, _, subject = line.partition("\t")
        if sha and pat.search(subject):
            out.append(sha)
    return out


def changed_files(repo: Path, start_commit: str, task_number: str | int | None = None,
                  ignore_untracked: bool = False) -> list[str]:
    """Files touched since start_commit: committed, staged, unstaged and untracked.

    With task_number, committed files are taken only from commits tagged `task N`
    (see task_commits); unattributed commits from other lanes are skipped. Staged
    and unstaged changes are always counted — they are live work in this checkout.
    ignore_untracked drops files git does not know about (shared checkouts carry
    other people's drafts); pass it consciously, never by default in single-lane repos.
    """
    files: set[str] = set()
    if task_number is None:
        files.update(l for l in git(repo, "diff", "--name-only", f"{start_commit}..HEAD").splitlines() if l)
    else:
        for sha in task_commits(repo, start_commit, task_number):
            files.update(l for l in git(repo, "show", "--pretty=", "--name-only", sha).splitlines() if l)
    files.update(l for l in git(repo, "diff", "--name-only", "HEAD").splitlines() if l)
    files.update(l for l in git(repo, "diff", "--name-only", "--cached").splitlines() if l)
    if not ignore_untracked:
        files.update(l for l in git(repo, "ls-files", "--others", "--exclude-standard").splitlines() if l)
    return sorted(files)


def head_commit(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").strip()


# --------------------------------------------------------------------------- #
# Reviewer reports — normalisation over the many shapes agents actually emit
# --------------------------------------------------------------------------- #

REPORT_NAME_RE = re.compile(r"^(?P<reviewer>[a-z][a-z0-9-]*?)-(?:round)?(?P<round>\d+)(?:[-.].*)?\.json$")

APPROVED_WORDS = ("approv", "pass", "accept", "ok", "clean")
REJECTED_WORDS = ("change", "reject", "fail", "block", "needs")


@dataclass
class Report:
    path: Path
    reviewer: str
    round: int
    status: str            # approved | approved_with_suggestions | changes_required | triaged | unknown
    findings: list[dict[str, Any]] = field(default_factory=list)
    closures: list[dict[str, Any]] = field(default_factory=list)


def normalise_status(raw: Any) -> str:
    s = str(raw or "").strip().lower().replace(" ", "_")
    if not s:
        return "unknown"
    if s in ("approved", "approve", "pass", "passed", "ok", "clean", "accept", "accepted"):
        return "approved"
    if s == "triaged":
        # Не вердикт ревьюера, а закрытие находок лидом (build-route шаг 6):
        # task-accept принимает его только без открытых находок.
        return "triaged"
    if s == "needs_improvement" or "suggest" in s or ("with_" in s and "approv" in s):
        return "approved_with_suggestions"   # test-reviewer: zero critical, some major
    if any(w in s for w in REJECTED_WORDS):
        return "changes_required"
    if any(w in s for w in APPROVED_WORDS):
        return "approved"
    return "unknown"


def _finding_text(f: dict[str, Any]) -> str:
    for key in ("summary", "issue", "suggestion", "title", "message", "description", "detail"):
        v = f.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return json.dumps(f, ensure_ascii=False, sort_keys=True)


def _finding_severity(f: dict[str, Any], default: str) -> str:
    sev = str(f.get("severity") or f.get("level") or "").strip().lower()
    if sev in ("critical", "blocker", "high"):
        return "critical"
    if sev in ("major", "medium"):
        return "major"
    if sev in ("minor", "low", "info", "nit", "suggestion"):
        return "minor"
    if f.get("optional") is True:
        return "minor"
    return default


def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())[:200]


def fingerprint(reviewer: str, file: str, category: str, text: str) -> str:
    key = "|".join([reviewer.lower(), norm_path(file or ""), (category or "").lower(), normalise_text(text)])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def parse_report(path: Path) -> Report | None:
    m = REPORT_NAME_RE.match(path.name)
    if not m:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    reviewer = str(data.get("reviewer") or m.group("reviewer"))
    rnd = int(data.get("round") or m.group("round"))
    raw_status = data.get("status") or data.get("verdict") or data.get("overall_verdict")
    status = normalise_status(raw_status)

    findings: list[dict[str, Any]] = []
    for item in data.get("criticalIssues") or []:
        if isinstance(item, dict):
            findings.append(_normalise_finding(reviewer, item, default_sev="critical"))
    for item in data.get("suggestions") or []:
        if isinstance(item, dict):
            findings.append(_normalise_finding(reviewer, item, default_sev="minor"))
    for item in (data.get("findings") or []) + (data.get("issues") or []):   # skill-checker uses issues[]
        if isinstance(item, dict):
            findings.append(_normalise_finding(reviewer, item, default_sev="major"))

    closures = [c for c in (data.get("closures") or []) if isinstance(c, dict)]
    return Report(path=path, reviewer=reviewer, round=rnd, status=status, findings=findings, closures=closures)


def _normalise_finding(reviewer: str, f: dict[str, Any], default_sev: str) -> dict[str, Any]:
    text = _finding_text(f)
    file = str(f.get("file") or f.get("path") or f.get("location") or "")
    category = str(f.get("category") or f.get("type") or "")
    return {
        "fingerprint": fingerprint(reviewer, file, category, text),
        "reviewer": reviewer,
        "severity": _finding_severity(f, default_sev),
        "file": file,
        "line": f.get("line"),
        "category": category,
        "text": text,
        "recommendation": f.get("recommendation") or f.get("suggested_fix") or f.get("fix") or "",
    }


def load_reports(log_dir: Path) -> list[Report]:
    if not log_dir.is_dir():
        return []
    reports = [r for r in (parse_report(p) for p in sorted(log_dir.glob("*.json"))) if r]
    return sorted(reports, key=lambda r: (r.reviewer, r.round))


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
