"""The README and GUIDE examples print what their comments say; docs and versions agree."""

from __future__ import annotations

import contextlib
import io
import itertools
import re
import shlex
from pathlib import Path
from urllib.parse import parse_qsl

import mailtourl
from mailtourl._cli import main

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "GUIDE.md").read_text(encoding="utf-8")


def _python_blocks(text: str = README) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def _expected_output(block: str) -> list[str]:
    """Each print line, or the loop that prints, is followed by comment lines with output."""
    expected: list[str] = []
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("#"):
            continue
        following = itertools.takewhile(lambda text: text.startswith("# "), lines[index + 1 :])
        expected.extend(text[2:] for text in following)
    return expected


def _run_blocks(text: str, name: str) -> tuple[int, int]:
    checked = 0
    blocks = _python_blocks(text)
    for block in blocks:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(block, name, "exec"), {"__name__": "docs"})
        expected = _expected_output(block)
        assert expected, block
        assert out.getvalue().splitlines() == expected
        checked += len(expected)
    return len(blocks), checked


def test_every_readme_example_runs_and_prints_its_comment() -> None:
    assert _run_blocks(README, "README.md") == (4, 10)


def test_every_guide_example_runs_and_prints_its_comment() -> None:
    assert _run_blocks(GUIDE, "GUIDE.md") == (7, 32)


def test_the_readme_links_are_absolute_and_carry_the_badge() -> None:
    for target in re.findall(r"\]\(([^)]+)\)", README):
        assert target.startswith("https://"), target
    image = "https://lianes8studio.com/certified/lianes8-certified-badge.svg"
    badge = f"[![Lianes8 Certified]({image})](https://lianes8studio.com/certified)"
    assert README.splitlines()[2] == badge
    for page in ("GUIDE.md", "CHANGELOG.md", "LICENSE"):
        assert f"https://github.com/JaviLianes8/mailtourl/blob/main/{page}" in README


def test_the_standard_library_output_quoted_in_the_readme_is_real() -> None:
    shown = parse_qsl("subject=1+1%0D%0ABcc:%20spy@evil.example")
    assert f"`{shown!r}`" in README


def test_every_command_line_example_prints_what_the_readme_shows() -> None:
    block = README.split("## Command line", 1)[1].split("```", 2)[1]
    lines = block.strip().splitlines()
    commands = [(index, line[2:]) for index, line in enumerate(lines) if line.startswith("$ ")]
    assert len(commands) == 2
    for index, command in commands:
        argv = shlex.split(command)
        assert argv[0] == "mailtourl"
        out = io.StringIO()
        assert main(argv[1:], stdout=out) == 0
        assert out.getvalue() == lines[index + 1] + "\n"


def test_the_api_table_lists_every_public_name() -> None:
    table = README.split("## API", 1)[1].split("\n## ", 1)[0]
    for name in mailtourl.__all__:
        assert f"`{name}" in table, name


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == mailtourl.__version__


def test_changelog_has_an_entry_for_this_version() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{mailtourl.__version__}]" in text


def test_no_em_dash_anywhere_in_the_tree() -> None:
    suffixes = {".py", ".md", ".toml", ".ps1", ".txt", ".yml", ".json"}
    for path in ROOT.rglob("*"):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if parts[:2] == ("tests", "upstream") and path.name != "MANIFEST.json":
            continue
        if any(
            (part.startswith(".") and part != ".github") or part == "__pycache__" for part in parts
        ):
            continue
        assert chr(0x2014) not in path.read_text(encoding="utf-8"), path


def test_source_files_stay_under_two_hundred_lines() -> None:
    for folder in ("src", "tests", "scripts"):
        for path in ROOT.joinpath(folder).rglob("*.py"):
            assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path
