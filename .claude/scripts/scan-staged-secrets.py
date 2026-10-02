#!/usr/bin/env python3
"""Поиск секретов в том, что уже добавлено в индекс (staged), без внешних зависимостей.

Зачем: gitleaks установлен не на каждой машине, а `ENGINEERING.md` §6 обещает защиту
от утечки. Этот скрипт — минимальная замена: работает всюду, где есть python3 и git.
Он не заменяет gitleaks, но закрывает то, на чём реально горят: ключ провайдера, токен бота,
приватный ключ, `.env` в индексе.

Запуск:
    python3 .claude/scripts/scan-staged-secrets.py          # проверить индекс
    python3 .claude/scripts/scan-staged-secrets.py --file X # проверить один файл

Коды: 0 — чисто, 1 — есть находки, 2 — ошибка запуска.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Каждое правило: имя, регулярка, короткое пояснение
RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"), "ключ OpenAI/совместимого провайдера"),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "ключ Anthropic"),
    ("telegram-token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}"), "токен Telegram-бота"),
    ("rest-webhook", re.compile(r"https?://[\w.-]+/rest/\d+/[A-Za-z0-9]{10,}"), "входящий REST-вебхук CRM с секретом в URL"),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), "приватный ключ"),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "ключ доступа AWS"),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "ключ Google API"),
    ("assigned-secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|webhook)\b\s*[=:]\s*['\"]?[A-Za-z0-9_\-/+]{16,}"),
        "переменной с секретным именем присвоено похожее на секрет значение"),
]
# Файлы, которым в индексе быть нельзя вообще
FORBIDDEN_PATHS = (re.compile(r"(^|/)\.env$"), re.compile(r"(^|/)\.env\.(?!example|template)[\w.-]+$"),
                   re.compile(r"(^|/)google_token\.json$"), re.compile(r"\.(pem|p12|pfx)$"))
# Что не проверяем: наши же правила и документация про секреты дают ложные срабатывания
SKIP_PATHS = (re.compile(r"^\.claude/scripts/scan-staged-secrets\.py$"),
              re.compile(r"^\.claude/skills/prod-review/"),
              re.compile(r"(^|/)\.env\.example$"))
# Бинарные форматы: секретов в тексте там не ищем, файл пропускаем с пометкой в stderr
BINARY_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff",
                     ".pdf", ".zip", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
                     ".docx", ".xlsx", ".pptx", ".odt", ".mp3", ".mp4", ".mov", ".wav", ".ogg",
                     ".woff", ".woff2", ".ttf", ".otf", ".sqlite", ".db", ".pyc")
PLACEHOLDER = re.compile(r"(?i)(your[_-]?|example|placeholder|xxx+|changeme|<[^>]+>|\.\.\.|dummy|fake|test[_-]?key)")


def staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                         capture_output=True, text=True, timeout=30, check=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def staged_content(path: str) -> bytes | None:
    # Bytes, not text: a staged PNG (first byte 0x89) used to crash the whole hook with
    # UnicodeDecodeError, so no commit carrying an image could pass.
    # None, not b"": a blob the scanner could not read must block the commit by name —
    # an empty result would pass as "clean", and a failed tool is not a clean result.
    try:
        return subprocess.run(["git", "show", f":{path}"], capture_output=True,
                              timeout=30, check=True).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def is_binary(path: str, data: bytes) -> bool:
    # Same heuristic as git itself (NUL in the first 8 KiB) plus known binary extensions,
    # because a compressed format can go 8 KiB without a NUL.
    return path.lower().endswith(BINARY_EXTENSIONS) or b"\0" in data[:8192]


def scan_text(path: str, text: str) -> list[str]:
    problems = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:  # минифицированное или бинарное — не разбираем
            continue
        for name, rx, human in RULES:
            m = rx.search(line)
            if not m:
                continue
            if PLACEHOLDER.search(m.group(0)):
                continue  # очевидная заглушка
            snippet = m.group(0)
            masked = snippet[:6] + "…" + snippet[-2:] if len(snippet) > 12 else "…"
            problems.append(f"{path}:{lineno} [{name}] {human} ({masked})")
    return problems


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--file":
        if len(argv) < 2:
            print("нужен путь после --file")
            return 2
        p = Path(argv[1])
        problems = []
        if p.exists():
            data = p.read_bytes()
            if is_binary(str(p), data):
                print(f"binary, skipped: {p}", file=sys.stderr)
            else:
                problems = scan_text(str(p), data.decode("utf-8", errors="surrogateescape"))
    else:
        try:
            files = staged_files()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            print(f"не смог получить индекс git: {exc}")
            return 2
        problems = []
        for path in files:
            if any(rx.search(path) for rx in FORBIDDEN_PATHS):
                problems.append(f"{path} — такому файлу в git места нет (секреты/ключи)")
                continue
            if any(rx.search(path) for rx in SKIP_PATHS):
                continue
            data = staged_content(path)
            if data is None:
                problems.append(f"{path} — сканер не смог прочитать файл из индекса; это не находка, "
                                f"а сбой проверки: проверь файл руками")
                continue
            if is_binary(path, data):
                print(f"binary, skipped: {path}", file=sys.stderr)
                continue
            # surrogateescape: a non-UTF-8 text file (cp1251 etc.) is still scanned, never crashes
            problems += scan_text(path, data.decode("utf-8", errors="surrogateescape"))

    if problems:
        print("Похоже на секреты в том, что коммитится:")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nНастоящий секрет — сними файл с индекса (git restore --staged <путь>) и убери значение в .env.")
        print("Ложное срабатывание — почини сканер (правило или SKIP_PATHS в этом скрипте) отдельным коммитом.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
