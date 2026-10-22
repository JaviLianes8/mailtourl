"""Compare with independent implementations: Perl's URI::mailto and Python's email parser.

Perl's URI distribution (URI::mailto, a decoder written separately from this library) is
run when `perl` with the URI module is on PATH; the test skips otherwise. Three of its
behaviours, read in its source (URI 5.34), are kept out of the generated input: it reads
"+" as a space outside the path, turns a space in the path into "+", and splits fields
on ";" as well as "&".
"""

from __future__ import annotations

import random
import re
import shutil
import subprocess
from email.headerregistry import Address

import pytest

from mailtourl import Mailto, is_address, parse
from mailtourl._address import split_address

PERL = shutil.which("perl")

PERL_SCRIPT = r"""
use URI;
while (my $line = <STDIN>) {
    chomp $line;
    my @pairs = URI->new($line)->headers;
    print join(" ", map { unpack("H*", $_) } @pairs), "\n";
}
"""


def _perl_has_uri() -> bool:
    if PERL is None:
        return False
    found = subprocess.run([PERL, "-MURI::mailto", "-e", "1"], capture_output=True, check=False)
    return found.returncode == 0


def _perl_fields(uris: list[str]) -> list[list[tuple[str, str]]]:
    assert PERL is not None
    done = subprocess.run(
        [PERL, "-e", PERL_SCRIPT],
        input="".join(f"{uri}\n" for uri in uris).encode("ascii"),
        capture_output=True,
        check=True,
        timeout=120,
    )
    result = []
    for line in done.stdout.decode("ascii").splitlines():
        texts = [bytes.fromhex(item).decode("utf-8") for item in line.split(" ")]
        result.append(list(zip(texts[::2], texts[1::2], strict=True)))
    return result


def _as_mailto(fields: list[tuple[str, str]]) -> Mailto:
    """RFC 6068 section 2 and 3 field rules applied to the decoded pairs, written plainly."""
    slots: dict[str, list[str]] = {"to": [], "cc": [], "bcc": []}
    single: dict[str, str] = {}
    headers = []
    for name, value in fields:
        key = name.lower()
        if key in slots:
            slots[key] += [address for address in value.split(",") if address]
        elif key in ("subject", "body"):
            single.setdefault(key, value)
        else:
            headers.append((name, value))
    return Mailto(
        slots["to"],
        cc=slots["cc"],
        bcc=slots["bcc"],
        subject=single.get("subject"),
        body=single.get("body"),
        headers=headers,
    )


ATEXT = "abcXYZ019!#$%&'*-/=?^_`{|}~é納"
# Domain atoms hold only what a URI can carry raw or as UTF-8 (see build), less "+".
DOMAIN = "abcXYZ019-!$'*é納"
TEXT = "aZ9 -._~!$&'()*,=:@/?#[]%\"<>\\^`{|}\té納\U0001f600\r\n"


def _random_mailto(rng: random.Random) -> Mailto:
    def atoms(alphabet: str = ATEXT) -> str:
        parts = ("".join(rng.choice(alphabet) for _ in range(rng.randint(1, 4))) for _ in "ab")
        return ".".join(parts)

    def address() -> str:
        local = atoms() if rng.random() < 0.8 else '"' + rng.choice(['\\"', "a@b", "x;y"]) + '"'
        return f"{local}@{atoms(DOMAIN)}"

    def text(single_line: bool = True) -> str:
        pool = TEXT.replace("\r", "").replace("\n", "") if single_line else TEXT
        return "".join(rng.choice(pool) for _ in range(rng.randrange(12)))

    names = rng.sample(["Keywords", "In-Reply-To", "X-A", "x-b!#$%'*-.^_`|~"], rng.randint(0, 3))
    return Mailto(
        [address() for _ in range(rng.randint(0, 3))],
        cc=[address() for _ in range(rng.randint(0, 2))],
        bcc=[address() for _ in range(rng.randint(0, 2))],
        subject=rng.choice([None, text()]),
        body=rng.choice([None, re.sub(r"\r\n|\r|\n", "\r\n", text(single_line=False))]),
        headers=[(name, text()) for name in names],
    )


@pytest.mark.skipif(not _perl_has_uri(), reason="perl with the URI module is not installed")
def test_perl_uri_mailto_decodes_built_uris_to_the_same_fields() -> None:
    rng = random.Random(2368)
    mails = [_random_mailto(rng) for _ in range(3000)]
    uris = [mail.to_uri() for mail in mails]
    for mail, uri, fields in zip(mails, uris, _perl_fields(uris), strict=True):
        assert _as_mailto(fields) == mail, uri
        assert parse(uri) == mail == parse(uri, strict=True), uri


@pytest.mark.skipif(not _perl_has_uri(), reason="perl with the URI module is not installed")
def test_perl_uri_mailto_agrees_on_the_rfc_style_examples() -> None:
    uris = [
        "mailto:chris@example.com",
        "mailto:infobot@example.com?subject=current-issue",
        "mailto:infobot@example.com?body=send%20current-issue%0D%0Asend%20index",
        "mailto:list@example.org?In-Reply-To=%3C3469A91.D10AF4C@example.com%3E",
        "mailto:majordomo@example.com?body=subscribe%20bamboo-l",
        "mailto:joe@example.com?cc=bob@example.com&body=hello",
        "mailto:gorby%25kremvax@example.com",
        "mailto:unlikely%3Faddress@example.com?blat=foop",
        "mailto:Mike%26family@example.org",
        "mailto:%22not%40me%22@example.org",
        "mailto:%22oh%5C%5Cno%22@example.org",
        "mailto:user@example.org?subject=caf%C3%A9",
        "mailto:?to=addr1@an.example,addr2@an.example",
        "mailto:addr1@an.example?to=addr2@an.example",
        "MAILTO:a@x.example?Subject=one&subject=two&BODY=b&X-Y=1&x-y=2",
    ]
    for uri, fields in zip(uris, _perl_fields(uris), strict=True):
        assert parse(uri) == _as_mailto(fields), uri


def _unquoted(local: str) -> str:
    if not local.startswith('"'):
        return local
    out, index = [], 1
    while index < len(local) - 1:
        index += local[index] == "\\"
        out.append(local[index])
        index += 1
    return "".join(out)


def test_python_email_parser_reads_every_ascii_address_the_same_way() -> None:
    rng = random.Random(5322)
    local_pool = 'aZ9!#$%&\'*+-/=?^_`{|}~..""\\ ()<>,:;@'
    domain_pool = "aZ9-.[].[]:;\\ ()<>!#$%&'*+/=?^_`{|}~"
    checked = 0
    for _ in range(30000):
        local = "".join(rng.choice(local_pool) for _ in range(rng.randrange(1, 8)))
        domain = "".join(rng.choice(domain_pool) for _ in range(rng.randrange(1, 8)))
        text = f"{local}@{domain}"
        if not is_address(text):
            continue
        local, domain = split_address(text)
        address = Address(addr_spec=text)
        assert (address.username, address.domain) == (_unquoted(local), domain), text
        checked += 1
    assert checked > 1000
