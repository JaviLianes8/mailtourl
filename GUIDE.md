# mailtourl guide

The behaviour of every public name in detail. Each Python block below runs as a test:
the comment lines after a statement hold what it prints.

## Reading a URI: `parse`

`parse(uri, *, strict=False)` returns a `Mailto`. It reads text in one of two modes.

**Default: like a browser.** The text is first cleaned the way the WHATWG URL Standard
cleans a link before it parses it: leading and trailing C0 controls and spaces are
stripped and every tab, LF and CR is removed. Only this cleaning is applied: when the
address part starts with `/`, a browser also drops `.` and `..` path segments before it
hands the link over, and `parse` keeps them. Then:

- The scheme is matched without case and the fragment (`#...`) is dropped.
- Recipients come from the path and from every `to`, `cc` and `bcc` field, in order. The
  path and those fields are split on raw commas before decoding, so `%2C` stays inside
  an address. Each address is trimmed of whitespace; empty ones are skipped.
- Field names are percent-decoded and trimmed before they are classified, so `%62cc` and
  ` bcc` are `bcc`. A name that is still not an RFC 5322 field name (a colon, a control,
  a space, non-ASCII) is dropped with its value.
- The first `subject` and the first `body` win; every other field is kept in `headers`,
  repeats included, in URI order.
- Values are percent-decoded as UTF-8; a broken escape stays as written and bytes that
  are not UTF-8 become U+FFFD. A `+` is never read as a space (RFC 6068 section 5).

```python
from mailtourl import parse

uri = (
    " mailto:a@x.example,%20b@x.example?subject=one&SUBJECT=two"
    "&%62cc=c@x.example&X-Tag=1&x-tag=2&body=a%0D%0Ab#top\n"
)
mail = parse(uri)
print(mail.to, mail.bcc)
# ('a@x.example', 'b@x.example') ('c@x.example',)
print(mail.subject, repr(mail.body))
# one 'a\r\nb'
print(mail.headers)
# (('X-Tag', '1'), ('x-tag', '2'))
print(parse("mailto:a@x.example?Bcc%3A=spy@evil.example&subject=1+1%3D2").safe())
# Mailto(to=('a@x.example',), cc=(), bcc=(), subject='1+1=2', body=None, headers=())
```

**Header injection is refused in both modes.** Outside the body, a decoded NUL or any
character `str.splitlines` breaks on (CR, LF, VT, FF, the file, group and record
separators, NEL, U+2028, U+2029) raises `MailtoError`, whatever field it is in, the
recipients included. The body may hold line breaks: it is the message text.

```python
from mailtourl import MailtoError, parse

for uri in ("mailto:a@x.example?subject=a%0Db", "mailto:a%0A@x.example", "mailto:?X=%E2%80%A8"):
    try:
        parse(uri)
    except MailtoError as error:
        print(error.reason, error.offset)
# '\r' in the subject field: header injection 28
# '\n' in the to address: header injection 8
# '\u2028' in the X field: header injection 10
```

**`strict=True`: exactly RFC 6068.** The text must match the section 2 grammar:

- Only the characters the grammar allows may stay raw in each part (`pchar` in the path,
  `qchar` in field names and values); every `%` starts a complete escape, and the
  decoded bytes are UTF-8.
- Every recipient is an addr-spec and the `@` before its domain is not percent-encoded.
  In a domain name, escapes may only spell UTF-8 (section 2, item 4); a domain literal
  (`[...]`) holds printable ASCII but `[`, `]` and `\`. This is the form `is_address`
  checks, except that a domain name in the path may hold a raw `&` or `=`: erratum 7919
  allows them there, but `build` never writes them, so `is_address` and `safe()` refuse
  such an address and `to_uri` raises for it.
- Field names are RFC 5322 field names, a field is never empty and has an `=`, no field
  name appears twice (ignoring case: the grammar allows it, section 2 advises against
  it), body line breaks are CRLF, there is no control but tab outside the body and no
  fragment.
- `MailtoError.offset` is the index in `uri` of the first character that breaks a rule;
  for an escape, the `%` that starts it. Default-mode offsets point the same way, after
  bytes that are not UTF-8 too.

```python
from mailtourl import MailtoError, parse

for uri in (
    "mailto:a@x.example?subject=Hi&subject=again",
    "mailto:a@x.example?body=a%0Ab",
    "mailto:a@ex%61mple.com",
    "mailto:j%20d@x.example",
    "mailto:a@x.example#top",
):
    try:
        parse(uri, strict=True)
    except MailtoError as error:
        print(error.reason, error.offset)
# header field 'subject' repeated 30
# body line break not written as %0D%0A 25
# percent-encoding of ASCII in a domain name 11
# character ' ' not allowed in local part 'j d' 7
# a mailto: URI takes no fragment 18
print(parse("mailto:%22j%5C%20d%22@x.example", strict=True).to)
# ('"j\\ d"@x.example',)
```

Whatever `strict=True` accepts, the default mode reads to the same value.

## The `Mailto` value

`Mailto` is a frozen, hashable dataclass with six fields: `to`, `cc` and `bcc` (tuples of
`str`), `subject` and `body` (`str` or `None`) and `headers` (a tuple of `(name, value)`
pairs). The constructor takes a `str`, any iterable of `str` or `None` for each recipient
list and a mapping, `(name, value)` pairs or `None` for `headers`, like `build`;
everything but `to` is keyword-only. It stores tuples of plain `str` and raises
`TypeError` for anything else, but it does not validate addresses or header names:
`to_uri` does.

- `recipients`: `to + cc + bcc`.
- `header(name)` and `header_all(name)`: the first value and every value of the fields
  called `name` in `headers`, ignoring case. `header` returns `None` when there is none.
- `safe(allow=("keywords",))`: a copy that `to_uri` always writes. It keeps the
  recipients `is_address` accepts; subject and body unless they hold a control character
  `build` refuses; and, of the headers named in `allow` (ignoring case), the first of each
  name that `build` accepts. RFC 6068 section 4 calls only subject, keywords and body
  safe in general; widen `allow` for sources you trust.
- `to_uri()`: the URI, built with the same rules and checks as `build`. It raises
  `MailtoError` for whatever `build` refuses, whichever mode read the value: strict mode
  accepts a `From` field and a raw `&` in a domain name of the path, the default mode a
  control character in the subject. Call `safe()` first to drop them.

```python
import dataclasses
import pickle
from mailtourl import Mailto, parse

mail = Mailto(
    ["a@x.example", "Eve <e@x.example>"],
    cc="b@x.example",
    headers={"In-Reply-To": "<1@x>", "X-Tag": "t"},
)
print(mail.recipients)
# ('a@x.example', 'Eve <e@x.example>', 'b@x.example')
print(mail.header("in-reply-to"), mail.header("Keywords"))
# <1@x> None
print(mail.safe(allow=["In-Reply-To"]))
# Mailto(to=('a@x.example',), cc=('b@x.example',), bcc=(), subject=None, body=None, headers=(('In-Reply-To', '<1@x>'),))
print(dataclasses.replace(mail.safe(), subject="Re: hi").to_uri())
# mailto:a@x.example?cc=b@x.example&subject=Re:%20hi
same = Mailto(list(mail.to), cc=mail.cc, headers=mail.headers)
print(pickle.loads(pickle.dumps(mail)) == mail, len({mail, same}))
# True 1
read = parse("mailto:a@x.example,b@x&y.example?subject=%01&Keywords=k&keywords=l")
print(read.safe().to_uri())
# mailto:a@x.example?Keywords=k
```

## Writing a URI: `build`

`build(to=None, *, cc=None, bcc=None, subject=None, body=None, headers=None)` returns a
URI that passes through a browser unchanged and reads back, in either mode, to the same
value (body line breaks as CRLF). Each recipient argument is a `str` or an iterable of
`str`; `headers` is a mapping or `(name, value)` pairs, kept in order.

- Addresses are written with every character the URI cannot hold raw percent-encoded,
  plus `,`, `&`, `;` and `=` (valid under both readings of RFC 6068 erratum 7919) and an
  `@` inside a quoted local part. Non-ASCII is written as UTF-8 escapes.
- Field values keep raw only the RFC 6068 `qchar` set less `+`, which form decoders read
  as a space. Hex digits are upper case.
- Body line breaks (CR, LF or CRLF) are written as `%0D%0A` (RFC 6068 section 5).
- Fields come out in a fixed order: `cc`, `bcc`, `subject`, `body`, then `headers`.

```python
from mailtourl import build

print(build("a@x.example", subject="100% +1 ;-) a/b?c=d&e", body="x\ny\r\nz"))
# mailto:a@x.example?subject=100%25%20%2B1%20;-)%20a%2Fb%3Fc%3Dd%26e&body=x%0D%0Ay%0D%0Az
print(build('"j\\ d"@x.example', cc=["Δ@x.example", "u@例え.jp"]))
# mailto:%22j%5C%20d%22@x.example?cc=%CE%94@x.example,u@%E4%BE%8B%E3%81%88.jp
print(build("a@[IPv6:2001:db8::1]", headers=[("X-A", "1"), ("Keywords", "k")]))
# mailto:a@%5BIPv6:2001:db8::1%5D?X-A=1&Keywords=k
```

`build` raises `MailtoError` for input it cannot write safely, and `TypeError` for
arguments of the wrong type:

```python
from mailtourl import MailtoError, build

for arguments in (
    {"to": "Jane <j@x.example>"},
    {"to": "a@x&y.example"},
    {"subject": "a\rb"},
    {"body": "a\x00b"},
    {"headers": {"Subject": "x"}},
    {"headers": {"Content-Type": "text/html"}},
    {"headers": [("X-A", "1"), ("x-a", "2")]},
    {"headers": {"X A": "1"}},
):
    try:
        build(**arguments)
    except MailtoError as error:
        print(error)
# to: character ' ' not allowed in local part 'Jane <j'
# to: '&' cannot be written in a domain name
# control character '\r' in subject
# control character '\x00' in body
# pass 'subject' through its own argument, not headers
# RFC 6068 section 3 says clients MUST ignore 'Content-Type'
# header 'x-a' given twice
# 'X A' is not an RFC 5322 header field name
```

The fields RFC 6068 section 3 says a client must ignore are refused by name: `From`,
`Sender`, `Reply-To`, `Date`, `Apparently-To`, `Received`, `Return-Path` and every
`Resent-*`, `Content-*` and `MIME-*` field. `to`, `cc`, `bcc`, `subject` and `body` go
through their own arguments. `Mailto.to_uri` applies the same checks, so a value read in
either mode may need `safe()` before it builds. In HTML, escape the `&` of the result
(`html.escape`).

## Addresses: `is_address`

`is_address(text)` is true when `text` is an RFC 5322 addr-spec in the form RFC 6068
section 2 allows: a dot-atom or quoted local part, then `@`, then a dot-atom domain or a
domain literal. Comments, obsolete forms, display names and whitespace (bare, or inside
quotes without a backslash) are refused. A domain name may not hold an ASCII character
that would need an escape (`` # % & / = ? ^ ` { | } ``): RFC 6068 allows escapes in a
domain name only for UTF-8, so no URI could carry it. `is_address(text)` is true exactly
when `build(text)` can write `text`.

Non-ASCII is allowed (RFC 6532) except what would hide what a reader sees: the
characters in the Unicode categories Cc, Cf, Cs, Zs, Zl and Zp (controls, formatting
characters, surrogates and separators) other than the joiners U+200C and U+200D, which
IDNA allows, and the noncharacters (U+FDD0 to U+FDEF and the last two code points of
every plane). Unassigned code points are allowed. The categories come from the
`unicodedata` module of the running Python (`unicodedata.unidata_version`), so a code
point a later Unicode version assigns to one of those categories can be accepted by an
older interpreter and refused by a newer one.

```python
from mailtourl import is_address

good = ["a.b+tag@x.example", '"a\\ b"@x.example', "é@例え.jp", "a/b@x.example"]
bad = ["a..b@x.example", "a@x.example (Jane)", "a\u200b@x.example", "a@x/y.example"]
print([is_address(text) for text in good], [is_address(text) for text in bad])
# [True, True, True, True] [False, False, False, False]
print(is_address("a@[192.0.2.1]"), is_address("a b@x.example"))
# True False
```

## Errors

`MailtoError(reason, offset=None)` is a `ValueError`. `reason` is the message without
the position and `offset` is the index in the parsed string where the problem starts, or
`None` for the builder's errors. A message quotes at most 60 characters of the input. Arguments of the
wrong type (bytes, numbers, `None` where a string is needed) raise `TypeError`. The
exception types and `reason`/`offset` are part of the stable API; the wording of the
messages is not.

## Command line

```
mailtourl parse [--strict] [--safe] [URI]
mailtourl build [--to ADDRESS]... [--cc ADDRESS]... [--bcc ADDRESS]... [--subject TEXT] [--body TEXT] [--header NAME=VALUE]...
```

`parse` prints the fields as one line of JSON (ASCII, so it survives any console) and
reads standard input when `URI` is left out; `--safe` applies `Mailto.safe()`. Standard
input is decoded as UTF-8 whatever the locale or console code page (a leading byte order
mark is skipped) and loses one trailing line ending (LF, CRLF or CR) and nothing else, so
piped text reads exactly like the same text given as `URI`; bytes that are not UTF-8
exit with status 2. `build` prints the URI. An invalid input exits with status 2 and the
reason on standard error; `python -m mailtourl` works the same way.

## Stability

From 1.0.0 the five public names, their signatures and defaults, the fields of
`Mailto`, the exception types, `MailtoError.reason` and `offset`, and the command line
options follow Semantic Versioning. Error message wording may improve in a minor release.
