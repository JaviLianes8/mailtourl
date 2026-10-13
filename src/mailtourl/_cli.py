"""Command line: read a mailto: URI into JSON, or build one from flags."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from ._build import build
from ._errors import MailtoError
from ._model import Mailto
from ._parse import parse


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mailtourl", description="Read or write mailto: URIs.")
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("parse", help="print the fields of a mailto: URI as JSON")
    read.add_argument("uri", nargs="?", help="the URI; read from standard input when absent")
    read.add_argument("--strict", action="store_true", help="reject input outside RFC 6068")
    read.add_argument(
        "--safe", action="store_true", help="drop headers other than keywords (RFC 6068 4)"
    )
    write = commands.add_parser("build", help="print a mailto: URI built from the options")
    for flag in ("--to", "--cc", "--bcc"):
        write.add_argument(flag, action="append", default=[], metavar="ADDRESS")
    write.add_argument("--subject")
    write.add_argument("--body")
    write.add_argument(
        "--header", action="append", default=[], metavar="NAME=VALUE", help="another field"
    )
    return parser


def _as_json(mail: Mailto) -> dict[str, object]:
    return {
        "to": list(mail.to),
        "cc": list(mail.cc),
        "bcc": list(mail.bcc),
        "subject": mail.subject,
        "body": mail.body,
        "headers": [list(pair) for pair in mail.headers],
    }


def main(
    argv: Sequence[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None
) -> int:
    """Run the ``mailtourl`` command and return its exit status."""
    args = _parser().parse_args(argv)
    out = stdout or sys.stdout
    try:
        if args.command == "parse":
            text = args.uri if args.uri is not None else (stdin or sys.stdin).read().strip()
            mail = parse(text, strict=args.strict)
            # ASCII output cannot fail on a console or pipe that lacks a character.
            json.dump(_as_json(mail.safe() if args.safe else mail), out, ensure_ascii=True)
        else:
            headers: list[tuple[str, str]] = []
            for item in args.header:
                name, equals, value = item.partition("=")
                if not equals:
                    raise MailtoError(f"--header expects NAME=VALUE, got {item!r}")
                headers.append((name, value))
            out.write(
                build(
                    args.to,
                    cc=args.cc,
                    bcc=args.bcc,
                    subject=args.subject,
                    body=args.body,
                    headers=headers,
                )
            )
    except MailtoError as error:
        print(f"mailtourl: {error}", file=sys.stderr)
        return 2
    out.write("\n")
    return 0
