"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from mailtourl import Mailto, MailtoError, build, is_address, parse
mail = parse("mailto:a@x.example")
reveal_type(mail)
reveal_type(mail.to)
reveal_type(mail.subject)
reveal_type(mail.headers)
reveal_type(mail.recipients)
reveal_type(mail.header("k"))
reveal_type(mail.header_all("k"))
reveal_type(mail.safe())
reveal_type(mail.to_uri())
reveal_type(build("a@x.example", headers={"K": "v"}))
reveal_type(is_address("a@x.example"))
reveal_type(MailtoError("r").offset)
reveal_type(MailtoError("r").reason)
parse(b"mailto:")
parse("mailto:", True)
build(subject=1)
Mailto(to=[1])
mail.header(1)
"""

REVEALED = [
    "mailtourl._model.Mailto",
    "tuple[str, ...]",
    "str | None",
    "tuple[tuple[str, str], ...]",
    "tuple[str, ...]",
    "str | None",
    "tuple[str, ...]",
    "mailtourl._model.Mailto",
    "str",
    "str",
    "bool",
    "int | None",
    "str",
]


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    args = ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    try:
        from mypy import api
    except ImportError:
        # The interpreter running pytest may lack mypy while the one on PATH has it.
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        result = subprocess.run([program, *args], capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def _lines(output: str, kind: str) -> dict[int, str]:
    found: dict[int, str] = {}
    for match in re.finditer(rf"snippet\.py:(\d+): {kind}: (.*)", output):
        found[int(match.group(1))] = match.group(2)
    return found


def test_the_public_names_have_the_documented_types(mypy_output: str) -> None:
    notes = _lines(mypy_output, "note")
    revealed = [notes[line] for line in sorted(notes) if notes[line].startswith("Revealed")]
    assert revealed == [f'Revealed type is "{name}"' for name in REVEALED], mypy_output


def test_arguments_of_the_wrong_type_are_type_errors(mypy_output: str) -> None:
    errors = _lines(mypy_output, "error")
    first = SNIPPET.splitlines().index('parse(b"mailto:")') + 1
    assert sorted(errors) == list(range(first, first + 5)), mypy_output
    assert all(
        text.endswith(("[arg-type]", "[list-item]", "[call-arg]")) for text in errors.values()
    ), mypy_output
