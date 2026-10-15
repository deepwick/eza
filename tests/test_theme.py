import gzip
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest
import yaml

from deepwick_spec.ansi import line_with, style_of
from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors


TREE_ROLES = {
    "src": "directory", "run.sh": "executable", "link": "symlink", "broken": "brokenSymlink",
    "pipe": "special", "bundle.tar.gz": "archive", "photo.png": "media", "notes.pdf": "document",
    "app.py": "source", "old.bak": "temp",
}


def tiny_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    header = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"\x00\x00")) + chunk(b"IEND", b"")


def make_tree(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir()
    (root / "run.sh").write_text("#!/bin/sh\necho run\n")
    (root / "run.sh").chmod(0o755)
    (root / "app.py").write_text("print('hi')\n")
    (root / "link").symlink_to("app.py")
    (root / "broken").symlink_to("missing")
    os.mkfifo(root / "pipe")
    (root / "bundle.tar.gz").write_bytes(gzip.compress(b"deepwick"))
    (root / "photo.png").write_bytes(tiny_png())
    (root / "notes.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (root / "old.bak").write_text("old\n")
    return root


def assert_role(text, name, role):
    style = style_of(text, name)
    expected = PALETTE.files[role]
    assert style["fg"] == C[expected.color].lower(), (name, role, style)
    assert style["bold"] == ("bold" in expected.style), (name, role, style)


EZA = shutil.which("eza")
requires_eza = pytest.mark.skipif(EZA is None, reason="requires eza")
SECTIONS = {
    "colourful", "filekinds", "perms", "size", "users", "links", "git", "git_repo", "security_context",
    "file_type", "punctuation", "date", "inode", "blocks", "header", "octal", "flags", "symlink_path",
    "control_char", "broken_symlink", "broken_path_overlay",
}


def theme():
    path = REPO / "deepwick.yml"
    assert path.is_file(), "deepwick.yml missing"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fg(style):
    return style["foreground"]


def test_sets_every_section():
    assert set(theme()) == SECTIONS


def test_file_roles_match_spec():
    t = theme()
    roles = {
        "directory": t["filekinds"]["directory"], "executable": t["filekinds"]["executable"],
        "symlink": t["filekinds"]["symlink"], "brokenSymlink": t["broken_symlink"],
        "special": t["filekinds"]["pipe"], "archive": t["file_type"]["compressed"],
        "media": t["file_type"]["image"], "document": t["file_type"]["document"],
        "source": t["file_type"]["source"], "temp": t["file_type"]["temp"],
        "permRead": t["perms"]["user_read"], "permWrite": t["perms"]["user_write"],
        "permExec": t["perms"]["user_execute_file"], "size": t["size"]["number_byte"],
        "user": t["users"]["user_you"], "group": t["users"]["group_yours"], "date": t["date"],
    }
    for role, style in roles.items():
        expected = PALETTE.files[role]
        assert fg(style) == C[expected.color], role
        assert style.get("is_bold", False) == ("bold" in expected.style), role


def test_git_columns_match_ui_roles():
    git = theme()["git"]
    assert fg(git["new"]) == C["teal"]
    assert fg(git["modified"]) == C["blue"]
    assert fg(git["deleted"]) == C["red"]
    assert fg(git["ignored"]) == C["muted"]


def run_eza(tmp_path, tree, **extra_env):
    config = tmp_path / "eza-config"
    config.mkdir(exist_ok=True)
    shutil.copy(REPO / "deepwick.yml", config / "theme.yml")
    env = {"PATH": f"{Path(EZA).parent}:/usr/bin:/bin", "HOME": str(tmp_path), "EZA_CONFIG_DIR": str(config), "LC_ALL": "C"}
    env.update(extra_env)
    return subprocess.run(
        [EZA, "-l", "--git", "--color=always", str(tree)],
        env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
    ).stdout


def git_tree(tmp_path):
    tree = make_tree(tmp_path / "tree")
    env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin"}
    git = ["git", "-C", str(tree), "-c", "user.name=Deepwick", "-c", "user.email=deepwick@example.invalid"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(tree)], check=True, env=env)
    subprocess.run([*git, "add", "app.py"], check=True, env=env)
    subprocess.run([*git, "commit", "-qm", "Initial commit"], check=True, env=env)
    (tree / "app.py").write_text("print('changed')\n")
    return tree


@requires_eza
def test_eza_renders_every_file_role(tmp_path):
    out = run_eza(tmp_path, git_tree(tmp_path))
    for name, role in TREE_ROLES.items():
        # eza paints a broken link's name as a symlink; the broken-link color goes on its target.
        assert_role(out, "missing" if name == "broken" else name, role)


@requires_eza
def test_eza_renders_git_and_permission_columns(tmp_path):
    out = run_eza(tmp_path, git_tree(tmp_path))
    assert style_of(out, "M")["fg"] == C["blue"].lower()
    assert style_of(out, "N")["fg"] == C["teal"].lower()
    assert style_of(out, "r")["fg"] == C["yellow"].lower()
    assert style_of(out, "w")["fg"] == C["red"].lower()
    assert style_of(out, "x")["fg"] == C["green"].lower()


@requires_eza
def test_ls_colors_overrides_theme(tmp_path):
    out = run_eza(tmp_path, make_tree(tmp_path / "tree"), LS_COLORS="di=31")
    assert style_of(out, "src")["fg"] == "ansi:1"


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []


def sgr_attrs(params):
    attrs, i = set(), 0
    while i < len(params):
        if params[i] in ("38", "48"):
            i += 5 if params[i + 1 : i + 2] == ["2"] else 3
            continue
        attrs.add(params[i])
        i += 1
    return attrs


@requires_eza
def test_file_types_drop_eza_default_bold_dim_underline(tmp_path):
    tree = make_tree(tmp_path / "tree")
    extra = ("song.flac", "a.mp4", "a.gpg", "Makefile", "a.o")
    for name in extra:
        (tree / name).write_text("x")
    out = run_eza(tmp_path, tree)
    for name in (*extra, "old.bak", "photo.png", "bundle.tar.gz", "notes.pdf", "app.py"):
        line = line_with(out, name)
        start = line.rindex("\x1b[", 0, line.index(name))
        sgr = line[start + 2 : line.index("m", start)].split(";")
        assert not ({"1", "2", "4"} & sgr_attrs(sgr)), (name, sgr)
