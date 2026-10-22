# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-22

The public API is now stable: the five names in `mailtourl.__all__` (`parse`, `build`,
`Mailto`, `MailtoError`, `is_address`), their signatures, defaults and error types, and
the `mailtourl` command (its options, the JSON that `parse` prints and its exit
statuses) follow Semantic Versioning from this release on. No release
before this one was published to PyPI. What is stable:

- Reading: `parse` reads a URI after the cleaning a browser applies to a link, or checks
  it against the RFC 6068 grammar with `strict=True`; in both modes a decoded line break
  or NUL outside the body raises `MailtoError` instead of reaching a header value.
- Writing: `build` and `Mailto.to_uri` encode every field, write body line breaks as
  `%0D%0A` and refuse input that would not survive the trip (invalid addresses, controls
  outside the body, fields RFC 6068 section 3 says clients must ignore).
- `Mailto`, a frozen, hashable value with `recipients`, `header`, `header_all` and
  `safe`, whose result `to_uri` always writes.
- `is_address` for the addr-spec form `build` can write into a `mailto:` URI.
- Errors: `MailtoError` (a `ValueError`) with `reason` and `offset`; `TypeError` for
  arguments of the wrong type.

### Changed

- `Mailto.header` and `Mailto.header_all` raise `TypeError` for a name that is not a
  `str` (they raised `AttributeError`).
- `Mailto` stores plain `str` values when given `str` subclasses, and its constructor,
  `build` and `Mailto.safe` raise `TypeError` with a clear message for a recipient list,
  header collection or allow list of the wrong type.
- `Mailto` and `MailtoError` report `mailtourl` as their module, so their reprs and
  pickles name `mailtourl.Mailto` and `mailtourl.MailtoError`, never a private module.
- Error messages quote at most 60 characters of the input: two strict-mode messages
  quoted a whole header field name, however long. A lone surrogate is reported by its
  code point.
- For input made only of spaces and controls, the "not a mailto: URI" error reports
  offset 0 instead of the length of the input.
- `python -m mailtourl` runs the command only when executed, not on import.
- `is_address` refuses a domain name holding an ASCII character that would need
  percent-encoding (`` # % & / = ? ^ ` { | } ``), so it is true exactly when `build` can
  write the address, and `Mailto.safe` drops such a recipient.
- `Mailto.safe` returns a value `to_uri` always writes: it also drops a subject or body
  holding a control character `build` refuses, every allowed header `build` refuses and
  the repeats of an allowed header name (the first one wins).
- `Mailto` takes `None` for `to`, `cc`, `bcc` and `headers`, now their defaults, as
  `build` does.
- The first parameter of `MailtoError` is named `reason`, like the attribute (it was
  `message`).
- `build`, `parse` and `is_address` report `mailtourl` as their module, and the
  signature of `build` spells out its parameter types instead of private aliases.
- `build`, `parse` and `is_address` read a `str` subclass as plain `str`, as `Mailto`
  does, so a subclass that overrides `__iter__` or `__len__` cannot hide a line break
  from the checks.
- The command reads standard input as UTF-8 whatever the locale (skipping a byte order
  mark) and drops one trailing line ending only, so piped text reads like an argument; it
  stripped all surrounding whitespace, decoded with the console code page on Windows and
  crashed on bytes that are not UTF-8, which now exit with status 2.
- `build` and `Mailto.to_uri` write a `+` in a `cc` or `bcc` address as `%2B`, as in
  every other field value, so a form decoder cannot read it as a space (RFC 6068
  section 5). A domain name holding `+` cannot be written that way (RFC 6068 allows no
  ASCII escape there), so `is_address` refuses it, `build` raises `MailtoError` for it
  and `Mailto.safe` drops it.
- An invalid header field name is reported by the character at fault ("character ':'
  not allowed in a header field name"), in `build` and in strict `parse`, instead of
  quoting the name, which a `Name: value` typo fills with the value. The command no
  longer echoes a `--header` argument that lacks `=`.
- `Mailto.safe(allow=None)` raises `TypeError`; it silently kept no header. `allow` is
  one name as a `str` or an iterable of names.
- `build` and `Mailto` read a `(name, value)` pair from what the tuple or list holds, so
  a subclass that overrides `__iter__`, `__len__` or `__getitem__` reads the same in
  both, and the constructor raises `TypeError` instead of `ValueError` for one that lies.
- The command exits with status 2 and one line ("no standard input", "no standard
  output") when the stream is missing (a closed descriptor, `pythonw`, a service); it
  crashed with a traceback and status 1.
- The help of `parse --safe` says it applies `Mailto.safe()`.

### Fixed

- In the default mode, `MailtoError.offset` pointed past the offending character, or
  past the end of the input, after percent-encoded bytes that are not UTF-8.
- Strict mode accepted a percent-encoded `@` before a domain literal when the quoted
  local part held a raw `@`; it now refuses it and points at the escaped `@`.
- In strict mode, "percent-encoded bytes are not UTF-8" pointed at the start of the
  field instead of the first escape that breaks UTF-8.
- The default mode kept a list of every character index, about 50 times the input in
  memory; it now needs no more than strict mode, and removing tabs and newlines costs at
  most a copy of the input.
- In strict mode, the offset of a malformed address or header field name pointed at
  where it starts; it now points at the character at fault (for something missing, such
  as the `@`, where it is missing). When a part breaks several rules, the offset is that
  of the first one in the text: a fragment, a raw character, a broken escape or bytes
  that are not UTF-8 no longer hide an earlier problem.
- A domain literal missing its closing `]` ("unterminated domain literal") or followed
  by more text ("text after the domain literal") is reported where the `]` is due or at
  the first character after it, in strict `parse` and in `build`; it was reported at the
  opening `[` as a character not allowed in a domain name.

### Added

- A runnable example in the docstring of every public name, run as doctests.
- A guide, `GUIDE.md`, with the behaviour of every public name in detail.

## [0.2.0] - 2026-10-13

### Added

- `parse(uri, strict=True)` checks the RFC 6068 grammar and raises `MailtoError` with
  the offset of the first problem; `MailtoError` gains `reason` and `offset`.
- `is_address` tells whether a string is an addr-spec a `mailto:` URI may carry.
- `Mailto.recipients`, `header`, `header_all`, `safe` and `to_uri`.
- A `mailtourl` command (and `python -m mailtourl`) with `parse` and `build`.

### Changed

- BREAKING: `Mailto` holds tuples instead of lists and `headers` is a tuple of
  `(name, value)` pairs instead of a dict; every argument but `to` is keyword-only.
- BREAKING: `build` raises `MailtoError` for input 0.1.0 wrote as is (see below), and
  body line breaks come out as `%0D%0A`.
- BREAKING: a decoded NUL or any line break `str.splitlines` knows, outside the body,
  raises `MailtoError` in every mode instead of reaching a header value. Field names are
  decoded and trimmed before they are classified, so an encoded or padded `bcc` lands in
  `bcc`, and in the default mode a name that is not a field name is dropped.
- `parse` applies the URL Standard preprocessing (leading and trailing controls and
  spaces stripped, tabs and newlines removed) and ignores the fragment.
- The first `subject` and `body` win; repeated other fields are all kept.
- `Mailto` is frozen and hashable: tuples for recipients and ordered `(name, value)`
  pairs for `headers`.
- `build` writes body line breaks as `%0D%0A`, encodes `@` inside a quoted local part
  and `+` in field values, and refuses invalid addresses, controls outside the body,
  header names that are not field names, repeated headers, headers that have their own
  argument and the fields RFC 6068 section 3 says clients must ignore.

## [0.1.0] - 2026-10-12

### Added

- First release: `parse` and `build` for `mailto:` URIs per RFC 6068, covering
  `to`, `cc` and `bcc` recipients, `subject`, `body` and other header fields,
  with correct percent-encoding in both directions.

[Unreleased]: https://github.com/JaviLianes8/mailtourl/commits/main
[1.0.0]: https://github.com/JaviLianes8/mailtourl/compare/74305ea...main
[0.2.0]: https://github.com/JaviLianes8/mailtourl/compare/e38d9ed...74305ea
[0.1.0]: https://github.com/JaviLianes8/mailtourl/commit/e38d9ed
