#!/usr/bin/env python3
"""Audit public repository files and reachable history for common leaks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


MAX_TEXT_BYTES = 1_000_000
SAFE_COMMIT_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class TextPattern:
    name: str
    regex: re.Pattern[str]


def build_patterns() -> tuple[TextPattern, ...]:
    private_source_terms = (
        "\u5468\u5305",
        "\u6b63\u6587\u5305",
        "\u8bf7\u6c42\u5468\u5305",
        "\u8bed\u6599\u5305",
        "\u79c1\u6709\u8bed\u6599",
        "\u6a21\u578b\u6807\u7b7e",
        "\u6e20\u9053\u7edf\u8ba1",
        "cor" + "pus",
        "weekly " + "bundle",
    )
    return (
        TextPattern(
            "absolute_user_path",
            re.compile(r"(?:/(?:Users|home)/[A-Za-z0-9._-]+(?:/|$)|[A-Za-z]:\\Users\\[^\\\s]+)", re.I),
        ),
        TextPattern("email_address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
        TextPattern("ipv4_address", re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")),
        TextPattern("phone_like", re.compile(r"(?<![0-9])1[3-9][0-9]{9}(?![0-9])")),
        TextPattern(
            "private_key_block",
            re.compile(r"-{5}BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-{5}"),
        ),
        TextPattern(
            "provider_token",
            re.compile(
                r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|"
                r"sk-[A-Za-z0-9_-]{32,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|"
                r"xox[baprs]-[A-Za-z0-9-]{10,}|AGE-SECRET-KEY-1[A-Z0-9]{40,})"
            ),
        ),
        TextPattern(
            "jwt_like",
            re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        ),
        TextPattern(
            "credential_assignment",
            re.compile(
                r"\b(?:api[_ -]?key|password|passwd|secret|access[_ -]?token|"
                r"refresh[_ -]?token|cookie)\s*[:=]\s*['\"]?[^\s'\"]{8,}",
                re.I,
            ),
        ),
        TextPattern("embedded_url_auth", re.compile(r"https?://[^/@\s]+:[^/@\s]+@", re.I)),
        TextPattern(
            "private_source_term",
            re.compile("|".join(re.escape(term) for term in private_source_terms), re.I),
        ),
        TextPattern(
            "hidden_unicode",
            re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]"),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def run_git(root: Path, *args: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return completed.stdout


def scan_text(label: str, data: bytes, patterns: tuple[TextPattern, ...]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if len(data) > MAX_TEXT_BYTES:
        return [{"category": "oversized_file", "location": label}]
    if b"\x00" in data:
        return [{"category": "binary_file", "location": label}]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return [{"category": "non_utf8_file", "location": label}]
    for pattern in patterns:
        if pattern.regex.search(text):
            findings.append({"category": pattern.name, "location": label})
    return findings


def audit_tracked_files(root: Path, patterns: tuple[TextPattern, ...]) -> tuple[int, list[dict[str, str]]]:
    output = run_git(root, "ls-files", "-z", binary=True)
    assert isinstance(output, bytes)
    paths = [Path(item.decode("utf-8")) for item in output.split(b"\x00") if item]
    findings: list[dict[str, str]] = []
    suspicious_names = {".env", "id_rsa", "id_ed25519"}
    suspicious_suffixes = {".pem", ".p12", ".key", ".sqlite", ".db", ".zip", ".7z", ".rar"}
    for relative in paths:
        if relative.name in suspicious_names or relative.suffix.lower() in suspicious_suffixes:
            findings.append({"category": "suspicious_filename", "location": str(relative)})
        findings.extend(scan_text(f"current:{relative}", (root / relative).read_bytes(), patterns))

    index = run_git(root, "ls-files", "-s")
    assert isinstance(index, str)
    for line in index.splitlines():
        mode, _, _, path = line.split(maxsplit=3)
        if mode == "120000":
            findings.append({"category": "symlink", "location": path})
        if mode == "160000":
            findings.append({"category": "submodule", "location": path})
    return len(paths), findings


def audit_history(root: Path, patterns: tuple[TextPattern, ...]) -> tuple[int, list[dict[str, str]]]:
    objects = run_git(root, "rev-list", "--objects", "--all")
    assert isinstance(objects, str)
    findings: list[dict[str, str]] = []
    seen_blobs: set[str] = set()
    for line in objects.splitlines():
        object_id, _, path = line.partition(" ")
        object_type = run_git(root, "cat-file", "-t", object_id)
        assert isinstance(object_type, str)
        if object_type.strip() != "blob" or object_id in seen_blobs:
            continue
        seen_blobs.add(object_id)
        data = run_git(root, "cat-file", "blob", object_id, binary=True)
        assert isinstance(data, bytes)
        label = f"history:{object_id[:12]}:{path or '<unknown>'}"
        findings.extend(scan_text(label, data, patterns))
    return len(seen_blobs), findings


def audit_commit_metadata(root: Path) -> tuple[int, list[dict[str, str]]]:
    output = run_git(root, "log", "--all", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce")
    assert isinstance(output, str)
    findings: list[dict[str, str]] = []
    commits = 0
    for line in output.splitlines():
        commit_id, author_name, author_email, committer_name, committer_email = line.split("\x00")
        commits += 1
        for role, name, email in (
            ("author", author_name, author_email),
            ("committer", committer_name, committer_email),
        ):
            if not SAFE_COMMIT_NAME.fullmatch(name):
                findings.append({"category": f"{role}_name", "location": commit_id[:12]})
            if not (
                email.endswith("@" + "users.noreply.github.com")
                or email == "noreply" + "@" + "github.com"
            ):
                findings.append({"category": f"{role}_email", "location": commit_id[:12]})
    return commits, findings


def run_self_test(patterns: tuple[TextPattern, ...]) -> None:
    samples = {
        "absolute_user_path": "/" + "Users" + "/example/private/file.txt",
        "email_address": "person" + "@" + "example.com",
        "ipv4_address": "192" + ".0.2.10",
        "phone_like": "138" + "00138000",
        "private_key_block": "-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5,
        "provider_token": "gh" + "p_" + "A" * 40,
        "jwt_like": "eyJ" + "A" * 12 + ".eyJ" + "B" * 12 + "." + "C" * 12,
        "credential_assignment": "api" + "key = " + "A" * 32,
        "embedded_url_auth": "https://user:" + "password" + "@" + "example.com/path",
        "private_source_term": "\u5468\u5305",
        "hidden_unicode": "safe" + "\u200b" + "text",
    }
    failures: list[str] = []
    for expected, sample in samples.items():
        matched = {pattern.name for pattern in patterns if pattern.regex.search(sample)}
        if expected not in matched:
            failures.append(expected)
    safe_sample = "Use ${CODEX_HOME:-$HOME/.codex}/skills and https://github.com/example/repository."
    if any(pattern.regex.search(safe_sample) for pattern in patterns):
        failures.append("safe_sample")
    result = {"ok": not failures, "patterns": len(patterns), "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


def main() -> None:
    args = parse_args()
    patterns = build_patterns()
    if args.self_test:
        run_self_test(patterns)
        return

    root = args.root.expanduser().resolve()
    tracked_files, tracked_findings = audit_tracked_files(root, patterns)
    history_blobs, history_findings = audit_history(root, patterns)
    commits, metadata_findings = audit_commit_metadata(root)
    findings = sorted(
        tracked_findings + history_findings + metadata_findings,
        key=lambda item: (item["category"], item["location"]),
    )
    result = {
        "ok": not findings,
        "tracked_files": tracked_files,
        "history_blobs": history_blobs,
        "commits": commits,
        "findings": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
