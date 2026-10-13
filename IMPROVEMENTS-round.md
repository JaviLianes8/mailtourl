# mailtourl improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 6068 and its errata, RFC 3986, RFC 5322, RFC 6532, WHATWG URL
- [x] Typed, frozen, hashable model with ordered header pairs
- [x] Address grammar: RFC 5322 addr-spec as restricted by RFC 6068, UTF-8 per RFC 6532
- [x] Parser: browser preprocessing, fragment dropped, merge rules, injection guard
- [x] Strict mode with `MailtoError` offsets
- [x] Safe builder: canonical encoding, CRLF bodies, refused headers and controls
- [x] Header safety: `Mailto.safe()` drops what RFC 6068 section 3 and 4 call unsafe
- [x] Command line: parse to JSON, build from flags
- [x] Contracts: pinned sources, README examples, browser round trip, installed wheel
- [x] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Mutation run: removing guarded logic makes the suite fail
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `parse`, `build`, a `Mailto` dataclass and `MailtoError`. Compared with the
sources below:

- `parse` never drops a fragment: `mailto:a@x?body=hi#top` yields the body `hi#top`, while
  RFC 6068 section 2 says a fragment is meaningless and should be ignored.
- A percent-encoded line break in `subject` or any other header (`%0D%0ABcc:...`) is
  decoded and returned as is. A mail client that copies the value into a header gets a
  second header line: the classic injection through hfields.
- A header name hidden behind encoding or padding (`%62cc`, `%20bcc`) is not recognised
  consistently, so a recipient can sit in `headers` instead of `bcc`.
- Invalid UTF-8 after percent-decoding becomes U+FFFD silently; there is no strict mode
  to validate a URI against the RFC 6068 grammar.
- Repeated `subject` or `body` fields: the last one silently wins; repeated other header
  fields collapse into one dict entry.
- `Mailto` is declared frozen but holds lists and a dict, so it is not hashable and can be
  changed in place.
- `build` writes anything: CR or LF in a subject or header, display names instead of
  addresses, header names that are not RFC 5322 field names, a `to` header that collides
  with the path. Body line breaks stay bare LF although section 5 says they MUST be
  encoded as `%0D%0A`. An `@` inside a quoted local part is left raw, unlike the RFC's own
  example, and `+` stays literal in field values although HTML-form style decoders read
  it as a space.
- Browser preprocessing (strip leading and trailing C0 controls and spaces, remove tabs
  and newlines anywhere) is not applied, so a link copied out of HTML parses differently
  from what the browser hands to the mail client.

## Sources (fetched 2026-10-13)

- RFC 6068, https://www.rfc-editor.org/rfc/rfc6068.txt: ABNF and encoding rules
  (section 2), semantics and fields that must be ignored (3), unsafe header fields (4),
  line breaks and `+` (5), examples (6).
- RFC 6068 errata, https://www.rfc-editor.org/errata/rfc6068: 7919 (verified) drops the
  requirement to encode `&`, `;` and `=` inside the address part; 4020 (verified) renames
  NO-WS-CTL to obs-NO-WS-CTL; 4706 (reported) notes that the escaped space in the section
  6.2 example is a quoted-pair, which the strict grammar here accepts.
- RFC 3986, https://www.rfc-editor.org/rfc/rfc3986.txt: unreserved, sub-delims, pchar,
  percent-encoding with upper-case hex (section 2.1).
- RFC 5322, https://www.rfc-editor.org/rfc/rfc5322.txt: atext, dot-atom-text,
  quoted-string, quoted-pair, dtext, field names (ftext).
- RFC 6532, https://www.rfc-editor.org/rfc/rfc6532.txt: UTF-8 in atext, qtext and dtext;
  header field names stay ASCII.
- WHATWG URL Standard, source `url.bs` in whatwg/url at commit
  fde3f74f063341a28d437216f75735b8b40128f5 (CC-BY-4.0): input preprocessing, the opaque
  path state and the query percent-encode set that browsers apply to `mailto:` links.
  Where Node.js is installed, its WHATWG `URL` is run as a live browser engine check.
- None of these files is committed. `tests/upstream/MANIFEST.json` records URL, revision,
  size, sha256 and licence, `scripts/fetch_upstream.py` fetches and checks them into the
  ignored `tests/upstream/` folder, and their tests skip while they are absent.

## Ranked improvements

1. **Header injection guard.** A decoded CR, LF or NUL in any field except `body`, or in
   an address, raises `MailtoError` in every mode. Header names are decoded and trimmed
   before they are classified, so `%62cc` and ` bcc` land in `bcc`, never hidden.
2. **Typed model.** `Mailto` is frozen and hashable: tuples for recipients, ordered
   `(name, value)` pairs for other headers (repeats kept), `header()` and `header_all()`
   with case-insensitive lookup, `recipients`, `to_uri()`.
3. **Parser per RFC 6068 and the browser view.** WHATWG preprocessing, fragment ignored,
   scheme case-insensitive, `to` merged from the path and every `to` field, `cc` and
   `bcc` merged likewise, first `subject` and `body` win, `+` never read as a space.
4. **Strict mode.** `parse(uri, strict=True)` holds the raw text to the grammar (pchar in
   the path per erratum 7919, qchar in fields), complete escapes, UTF-8 after decoding,
   every address an addr-spec (no obs forms, no bare whitespace, ASCII escapes only in a
   domain literal), field names RFC 5322 field names, body line breaks as CRLF, no
   repeated field, no fragment. Errors carry the offset.
5. **Safe builder.** Canonical encoding that reproduces the RFC examples byte for byte,
   `@` encoded inside the local part, `+` encoded in field values, body line breaks
   normalised to `%0D%0A`; refuses invalid addresses, controls outside the body, header
   names that are not field names, repeated names, names that collide with a dedicated
   argument, and fields RFC 6068 section 3 says a client MUST ignore.
6. **Header safety helper.** `Mailto.safe(allow=...)` keeps recipients, subject, body
   and the allowed headers (`keywords` by default, per section 4), dropping the rest.
7. **Address check.** `is_address(text)` exposes the addr-spec rule used by strict mode
   and the builder.
8. **Command line.** `mailtourl parse URI` prints JSON, `mailtourl build --to ...` prints
   a URI; exit 2 with the message on an invalid input. Useful when a shell script writes
   a link into a page or a template.
9. **Contracts.** RFC 6068 examples parsed and rebuilt byte for byte from the pinned file,
   character sets compared with the ABNF in the pinned RFCs, README examples executed,
   built URIs pass through a WHATWG `URL` unchanged, installed wheel and console script
   driven from an empty folder.
10. **Docs and packaging.** README with executed examples, API table and a security
    section, CHANGELOG, keywords and classifiers, sdist without planning notes or fetched
    files.

## Out of scope

- IDNA conversion of domains: the standard library only ships IDNA 2003, which RFC 5891
  replaced; UTF-8 percent-encoding, which RFC 6068 permits, is kept instead.
- MIME encoded words (RFC 2047) in field values: they are passed through as text.
- HTML escaping of `&` when a URI goes into markup: `html.escape` already does it.
- Display names and groups: RFC 6068 allows only addr-spec.

## Verification

- Gates on CPython 3.13.2 (this PC), 3.14.6 and 3.14.2 (two other Windows machines,
  fresh clones): `ruff format --check .`, `ruff check .`, `mypy --strict src` and
  `pytest`. With `MAILTOURL_E2E=1` the installed-wheel test builds the wheel and sdist,
  checks their contents (no planning notes, no fetched files, the manifest, the fetch
  script and the entry point present), installs the wheel in a fresh venv and drives the
  API, the `mailtourl` script and `python -m mailtourl` from an empty folder.
- Without the fetched files their tests skip; without Node.js the browser comparison
  skips; the rest of the suite passes either way.
- A seeded random round trip builds 3000 values and reads each back with the strict and
  the lenient parser.
- Guarded logic was removed one piece at a time (123 mutations, no bytecode, caches
  purged, a timeout per run, baseline green before and after). The first run left 13
  alive. Two were equivalent because the comma is split off before the character check,
  so the subtraction was removed; one (VCHAR versus space inside a quoted-pair) is
  equivalent because WSP is accepted there anyway and was dropped. The other ten were
  missing cases (a second hex digit, adjacent escapes, an escaped `~` in a domain, a raw
  `@` inside a quoted local part, the unit separator, an upper-case ignored field, type
  messages, a non-string `is_address` argument, a strict parse from standard input), now
  in `tests/test_mutation_gaps.py`. The rerun leaves none alive.
