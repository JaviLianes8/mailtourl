"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with MAILTOURL_E2E=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("MAILTOURL_E2E") != "1", reason="set MAILTOURL_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, pickle
import mailtourl
from mailtourl import Mailto, MailtoError, build, is_address, parse

assert "site-packages" in mailtourl.__file__, mailtourl.__file__
assert importlib.metadata.version("mailtourl") == mailtourl.__version__
assert importlib.resources.files("mailtourl").joinpath("py.typed").is_file()

uri = "mailto:%22not%40me%22@example.org?cc=b@x.example&subject=caf%C3%A9&body=a%0D%0Ab&K=v"
mail = parse(uri, strict=True)
assert mail == Mailto('"not@me"@example.org', cc="b@x.example", subject="café",
                      body="a\r\nb", headers={"K": "v"})
assert mail.to_uri() == uri and pickle.loads(pickle.dumps(mail)) == mail
assert parse(" mailto:a@x.example?%62cc=s@e.example#f\n").bcc == ("s@e.example",)
assert parse("mailto:?From=x@y.example&Keywords=k").safe().headers == (("Keywords", "k"),)
assert build(body="a\nb") == "mailto:?body=a%0D%0Ab" and is_address("a@[192.0.2.1]")
assert Mailto.__module__ == MailtoError.__module__ == "mailtourl"
import doctest, mailtourl._address, mailtourl._build, mailtourl._errors, mailtourl._parse
for module in (mailtourl, mailtourl._address, mailtourl._build, mailtourl._parse):
    found = doctest.testmod(module)
    assert found.failed == 0 and found.attempted > 0, (module, found)
for call in (
    lambda: parse("mailto:a@x.example?subject=a%0D%0ABcc:x@y.example"),
    lambda: parse("mailto:a@x.example#f", strict=True),
    lambda: build("Jane <j@x.example>"),
    lambda: build(headers={"From": "x@y.example"}),
):
    try:
        call()
    except MailtoError as error:
        assert isinstance(error, ValueError)
    else:
        raise AssertionError("expected MailtoError")
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False, timeout=600
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("mailtourl-*.whl")
    (sdist,) = dist.glob("mailtourl-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "mailtourl/py.typed" in names
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    dist_info = wheel.name.split("-py3-")[0] + ".dist-info"
    assert {name.split("/")[0] for name in names} == {"mailtourl", dist_info}
    assert f"{dist_info}/licenses/LICENSE" in names
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    assert "mailtourl = mailtourl._cli:main" in zipfile.ZipFile(wheel).read(entry_points).decode()
    metadata = zipfile.ZipFile(wheel).read(f"{dist_info}/METADATA").decode()
    assert "Classifier: Development Status :: 5 - Production/Stable" in metadata
    requires = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
    assert all("extra == 'dev'" in line for line in requires), requires
    assert "Requires-Python: >=3.10" in metadata
    checked = _run(sys.executable, "-m", "twine", "check", "--strict", wheel, sdist)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout.decode()
    assert "IMPROVEMENTS-round" not in listing and "CERT-1.0" not in listing
    for shipped in ("LICENSE", "README.md", "GUIDE.md", "CHANGELOG.md", "src/mailtourl/py.typed"):
        assert shipped in listing, shipped
    assert "tests/upstream/MANIFEST.json" in listing
    for fetched in ("rfc6068.txt", "rfc3986.txt", "rfc5322.txt", "rfc6532.txt", "url.bs"):
        assert fetched not in listing, fetched
    assert "tests/test_sources.py" in listing and "scripts/fetch_upstream.py" in listing

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    script = bindir / ("mailtourl.exe" if sys.platform == "win32" else "mailtourl")
    for command in ([script], [python, "-m", "mailtourl"]):
        shown = _run(*command, "parse", cwd=work, stdin=b"mailto:a@x.example?subject=Hi\n")
        assert shown.returncode == 0, shown.stderr
        assert json.loads(shown.stdout)["subject"] == "Hi"
        made = _run(*command, "build", "--to", "a@x.example", "--body", "a b", cwd=work)
        assert made.stdout.decode().strip() == "mailto:a@x.example?body=a%20b"
    failed = _run(script, "parse", "--strict", "mailto:a b@x.example", cwd=work)
    assert failed.returncode == 2 and b"must be percent-encoded" in failed.stderr
