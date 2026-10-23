# mailtourl

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse, validate and safely build `mailto:` URIs per RFC 6068.

- Reads a link after the cleaning a browser applies to it (outer spaces and C0
  controls, tabs, newlines, the fragment), or checks it against the RFC 6068 grammar with the
  offset of the first problem.
- Refuses header injection: a percent-encoded line break of any kind outside the body
  never comes back as a header value, and an encoded or padded `bcc` cannot hide a
  recipient.
- Builds URIs that pass through a browser unchanged, with every field encoded and body
  line breaks written as `%0D%0A`.
- Typed, frozen values, no dependencies, a command line for scripts.

The [guide](https://github.com/JaviLianes8/mailtourl/blob/main/GUIDE.md) describes every
public name in detail; the
[changelog](https://github.com/JaviLianes8/mailtourl/blob/main/CHANGELOG.md) lists what
changed in each release. From 1.0.0 the public API follows Semantic Versioning.

## Install

```
pip install mailtourl
```

## Usage

```python
from mailtourl import build, parse

uri = build(
    ["jane@example.com", "jack@example.com"],
    cc="team@example.com",
    subject="Re: café & tea",
    body="Hello\nWorld",
)
print(uri)
# mailto:jane@example.com,jack@example.com?cc=team@example.com&subject=Re:%20caf%C3%A9%20%26%20tea&body=Hello%0D%0AWorld

mail = parse(uri)
print(mail.to, mail.cc)
# ('jane@example.com', 'jack@example.com') ('team@example.com',)
print(repr(mail.subject), repr(mail.body))
# 'Re: café & tea' 'Hello\r\nWorld'
```

`parse` reads recipients from the path and from every `to`, `cc` and `bcc` field, in
order, decodes `subject` and `body` (the first of each wins) and keeps every other field
in `headers` as `(name, value)` pairs. Like a browser, it strips leading and trailing
C0 controls and spaces, removes tabs and newlines and ignores the fragment. A `+` is never
read as a space.

### Strict mode

```python
from mailtourl import MailtoError, parse

try:
    parse("mailto:joe@example.com?cc=bob@example.com?body=hello", strict=True)
except MailtoError as error:
    print(error.reason, error.offset)
# '?' must be percent-encoded in the cc address 41
```

`strict=True` holds the text to the RFC 6068 grammar: raw characters allowed in each
part, complete escapes that decode to UTF-8, every address an RFC 5322 addr-spec (no
comments, no obsolete forms, no whitespace) with an unencoded `@` before the domain,
ASCII escapes in a domain only inside a domain literal, field names that are RFC 5322
field names, no C0 or C1 control but tab in any field (the body also holds line breaks,
as CRLF) and no fragment. It also refuses a repeated field: the ABNF allows one, but
section 2 advises against it because clients disagree on what it means. The offset
points at the first offending character in the text, inside an address or a field name
too.

### Header injection and unsafe fields

```python
from mailtourl import MailtoError, parse

try:
    parse("mailto:a@example.com?subject=Hi%0D%0ABcc:%20spy@evil.example")
except MailtoError as error:
    print(error)
# '\r' in the subject field: header injection at offset 31

mail = parse("mailto:a@example.com?%62cc=spy@evil.example&From=boss@example.com&Keywords=k")
print(mail.bcc, mail.headers)
# ('spy@evil.example',) (('From', 'boss@example.com'), ('Keywords', 'k'))
print(mail.safe().headers)
# (('Keywords', 'k'),)
```

Outside the body, a decoded NUL or any character `str.splitlines` breaks on (CR, LF,
VT, FF, the file, group and record separators, NEL, U+2028, U+2029) raises
`MailtoError` in both modes. Field names are decoded and trimmed of whitespace before
they are classified, so `%62cc` or ` bcc` land in `bcc`; in the default mode a name that
is still not an RFC 5322 field name (a colon, a control, non-ASCII) is dropped. RFC 6068
section 4 calls only subject, keywords and body safe in general: `Mailto.safe(allow=...)`
keeps the recipients `is_address` accepts, subject, body and the first of each header you
allow, and drops whatever of those `to_uri` could not write, so its result always builds.

### Building

```python
from mailtourl import MailtoError, build

print(build('"not@me"@example.org', headers={"In-Reply-To": "<id@example.com>"}))
# mailto:%22not%40me%22@example.org?In-Reply-To=%3Cid@example.com%3E

for bad in ({"subject": "Hi\r\nBcc: x@y.example"}, {"headers": {"From": "x@y.example"}}):
    try:
        build("a@example.com", **bad)
    except MailtoError as error:
        print(error)
# control character '\r' in subject
# RFC 6068 section 3 says clients MUST ignore 'From'
```

`build` (and `Mailto.to_uri`) writes what RFC 6068 calls for: `@` encoded inside a quoted
local part, `+` encoded in field values (`cc` and `bcc` addresses included) so form
decoders cannot read it as a space, upper case hex, UTF-8 for anything outside ASCII. It
raises `MailtoError` for an address that is not an addr-spec (display names included), a
domain name holding `+` or an ASCII character that would need an escape, a control
character other than tab (and, in the body, line breaks), a header name that is not a
field name, a repeated header, a header that has its own argument, and the fields
RFC 6068 section 3 says a client must ignore (originator, routing, trace and MIME
fields). `Mailto.to_uri` applies the same checks, so a value read in either mode may
not build as is (strict mode accepts a `From` field, for one, and the default mode a
control character in the subject); `safe()` returns a copy that always builds. In HTML,
escape the `&` of the result with `html.escape`.

## Command line

```
$ mailtourl parse "mailto:a@example.com?subject=Hi&body=one%0D%0Atwo"
{"to": ["a@example.com"], "cc": [], "bcc": [], "subject": "Hi", "body": "one\r\ntwo", "headers": []}
$ mailtourl build --to a@example.com --subject "Re: 50% off" --header Keywords=sale
mailto:a@example.com?subject=Re:%2050%25%20off&Keywords=sale
```

`parse` takes `--strict` and `--safe` and reads standard input when the URI is left out,
as UTF-8 whatever the locale, less one line ending, so a pipe reads like an argument. An
invalid input exits with status 2 and the reason on standard error. `python -m mailtourl`
works the same way.

## API

| Name | What it does |
| --- | --- |
| `parse(uri, *, strict=False)` | Read a URI into a `Mailto`; strict mode checks the RFC 6068 grammar |
| `build(to, *, cc, bcc, subject, body, headers)` | Write a URI, refusing unsafe or invalid input |
| `Mailto` | Frozen value: `to`, `cc`, `bcc`, `subject`, `body`, `headers`, `recipients`, `header()`, `header_all()`, `safe()`, `to_uri()` |
| `MailtoError` | `ValueError` with `reason` and `offset` |
| `is_address(text)` | True for an addr-spec `build` can write (no whitespace, controls, invisible characters or noncharacters; no `+` or ASCII that would need an escape in a domain name) |

## Standards

RFC 6068 (with verified errata 7919 and 4020), RFC 3986, RFC 5322, RFC 6532 and the
WHATWG URL Standard. The tests read the RFC examples and grammar from pinned copies of
the published texts and compare the library with independent implementations: the
WHATWG `URL` class of Node.js, Perl's `URI::mailto` and the address parser of Python's
`email` package.

Not covered: IDNA conversion (the standard library only has IDNA 2003, so domains stay
UTF-8, which RFC 6068 allows), MIME encoded words (passed through as text), display
names (RFC 6068 allows only addr-spec) and the path normalisation a browser applies when
the address part starts with `/` (it drops `.` and `..` segments; `parse` keeps them).

## Why

Python's standard library has no `mailto:` codec. `urllib.parse.urlsplit` returns the
whole address list as one opaque path, and `urllib.parse.parse_qsl` on the query reads
`+` as a space and hands a percent-encoded line break back as is:
`parse_qsl("subject=1+1%0D%0ABcc:%20spy@evil.example")` gives
`[('subject', '1 1\r\nBcc: spy@evil.example')]`, a second header line waiting to be
copied into a message. Of the 22 packages on PyPI whose names contain "mailto" (checked
on 2026-10-22), `mailto-uri` (1.2.0, released in 2019) only builds URIs and leaves the
addresses unencoded; the others send, manage, analyse or validate email, render links or
redirect to webmail, and none parses a `mailto:` URI.
Other languages ship this: Ruby's `URI::MailTo`, Perl's `URI::mailto`, Android's
`android.net.MailTo` and Swift's `swift-rfc-6068`. `mailtourl` is a small, typed,
zero-dependency codec that reads like a browser, validates like the RFC and refuses
header injection in both directions.

## Development

`python scripts/fetch_upstream.py` downloads the RFCs and the URL Standard source listed
in `tests/upstream/MANIFEST.json` (they are not part of the repository; their tests skip
without them). The comparisons with Node.js and Perl run when `node`, and `perl` with the
URI module, are on PATH. `scripts/check.ps1` runs format, lint, types and tests. Set
`MAILTOURL_E2E=1` to also build the wheel and test the installed package.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/mailtourl/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
