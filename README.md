# mailtourl

Parse, validate and safely build `mailto:` URIs per RFC 6068.

- Reads a link the way a browser hands it to the mail client, or checks it against the
  RFC 6068 grammar with the offset of the first problem.
- Refuses header injection: a percent-encoded line break of any kind outside the body
  never comes back as a header value, and an encoded or padded `bcc` cannot hide a
  recipient.
- Builds URIs that pass through a browser unchanged, with every field encoded and body
  line breaks written as `%0D%0A`.
- Typed, frozen values, no dependencies, a command line for scripts.

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
controls and spaces, removes tabs and newlines and ignores the fragment. A `+` is never
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
field names, body line breaks as CRLF, no controls outside the body and no fragment. It
also refuses a repeated field: the ABNF allows one, but section 2 advises against it
because clients disagree on what it means. The offset points at the offending character.

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
keeps subject, body, the headers you allow and the recipients that are addr-specs.

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
local part, `+` encoded in field values so form decoders cannot read it as a space, upper
case hex, UTF-8 for anything outside ASCII. It raises `MailtoError` for an address that
is not an addr-spec (display names included), a domain name holding an ASCII character
that would need an escape, a control character outside the body, a header name that is
not a field name, a repeated header, a header that has its own argument, and the fields
RFC 6068 section 3 says a client must ignore (originator, routing, trace and MIME
fields). `Mailto.to_uri` applies the same checks, so a value read in the default mode
may not build as is: call `safe()` first. In HTML, escape the `&` of the result with
`html.escape`.

## Command line

```
$ mailtourl parse "mailto:a@example.com?subject=Hi&body=one%0D%0Atwo"
{"to": ["a@example.com"], "cc": [], "bcc": [], "subject": "Hi", "body": "one\r\ntwo", "headers": []}
$ mailtourl build --to a@example.com --subject "Re: 50% off" --header Keywords=sale
mailto:a@example.com?subject=Re:%2050%25%20off&Keywords=sale
```

`parse` takes `--strict` and `--safe` and reads standard input when the URI is left out;
an invalid input exits with status 2 and the reason on standard error. `python -m
mailtourl` works the same way.

## API

| Name | What it does |
| --- | --- |
| `parse(uri, *, strict=False)` | Read a URI into a `Mailto`; strict mode checks the RFC 6068 grammar |
| `build(to, *, cc, bcc, subject, body, headers)` | Write a URI, refusing unsafe or invalid input |
| `Mailto` | Frozen value: `to`, `cc`, `bcc`, `subject`, `body`, `headers`, `recipients`, `header()`, `header_all()`, `safe()`, `to_uri()` |
| `MailtoError` | `ValueError` with `reason` and `offset` |
| `is_address(text)` | True for an addr-spec a `mailto:` URI may carry (no whitespace, controls or invisible characters) |

## Standards

RFC 6068 (with verified errata 7919 and 4020), RFC 3986, RFC 5322, RFC 6532 and the
WHATWG URL Standard. The tests read the RFC examples and grammar from pinned copies
(`python scripts/fetch_upstream.py` fetches them; `tests/upstream/MANIFEST.json` lists
URL and sha256) and, when Node.js is installed, compare with its WHATWG `URL`.

Not covered: IDNA conversion (the standard library only has IDNA 2003, so domains stay
UTF-8, which RFC 6068 allows), MIME encoded words (passed through as text) and display
names (RFC 6068 allows only addr-spec).

## Why

The standard library does not model `mailto:` semantics: `urllib.parse` treats the
whole address list as an opaque path and never reads the `to`, `cc`, `bcc`, `subject` or
`body` fields, so the recipient split, the field encoding and the injection checks are
left to the caller. Other languages ship this (`URI::MailTo` in Ruby, `swift-rfc-6068`,
the Android `MailTo` class), but Python has no maintained equivalent. `mailtourl` fills
that gap with a small, typed, zero-dependency codec.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
