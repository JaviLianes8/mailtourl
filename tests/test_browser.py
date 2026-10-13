"""Compare with a live WHATWG URL implementation: the URL class of Node.js.

Skipped when `node` is not on PATH. Node implements the URL Standard that browsers use
to serialise a link before they hand it to the mail client.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess

import pytest

from mailtourl import build, parse

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

SCRIPT = """
let data = "";
process.stdin.on("data", (chunk) => (data += chunk));
process.stdin.on("end", () => {
  const out = JSON.parse(data).map((text) => {
    try { return new URL(text).href; } catch { return null; }
  });
  process.stdout.write(JSON.stringify(out));
});
"""


def _hrefs(uris: list[str]) -> list[str | None]:
    assert NODE is not None
    done = subprocess.run(
        [NODE, "-e", SCRIPT],
        input=json.dumps(uris).encode(),
        capture_output=True,
        check=True,
        timeout=60,
    )
    result: list[str | None] = json.loads(done.stdout)
    return result


def _random_text(rng: random.Random) -> str:
    pool = "aZ09 -._~!$&'()*+,;=:@/?#[]%\"<>\\^`{|}\t\r\né納\U0001f600"
    return "".join(rng.choice(pool) for _ in range(rng.randrange(12)))


def test_built_uris_pass_through_the_url_class_unchanged() -> None:
    rng = random.Random(6068)
    uris = [build('"a b"@x.example'.replace(" ", "\\ "), subject="café & tea")]
    for _ in range(400):
        text = _random_text(rng)
        uris.append(
            build(
                "a@x.example",
                subject=text.replace("\r", "").replace("\n", ""),
                body=text,
                headers={"X-Value": text.replace("\r", "").replace("\n", "")},
            )
        )
    assert _hrefs(uris) == uris


TRICKY = [
    "  mailto:a@x.example?subject=hi there  ",
    "\tmail\nto:a@x.exa\tmple?sub\rject=a\nb",
    "mailto:a@x.example?subject=café&body=納豆",
    "mailto:a b@x.example?subject=a b#frag",
    "mailto:a@x.example?subject=50%&body=%zz%FF",
    'mailto:a@x.example?subject=<b>"q"`x`',
    "mailto:a@x.example#?subject=lost",
    "MAILTO:A@X.EXAMPLE?Cc=c@x.example",
    "mailto:a@x.example?%62cc=b@x.example&+x=1",
    "\x01\x1f mailto:?to=a@x.example,b@x.example \x00",
]


@pytest.mark.parametrize("uri", TRICKY)
def test_the_lenient_reading_agrees_with_the_browser_serialisation(uri: str) -> None:
    (href,) = _hrefs([uri])
    assert href is not None
    assert parse(uri) == parse(href)
