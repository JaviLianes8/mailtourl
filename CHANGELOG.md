# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-22

The public API is now stable: the five names in `mailtourl.__all__` (`parse`, `build`,
`Mailto`, `MailtoError`, `is_address`), their signatures, defaults and error types, and
the `mailtourl` command follow Semantic Versioning from this release on. No release
before this one was published to PyPI.

### Stable

- Reading: `parse` reads a URI the way a browser hands it to the mail client, or checks
  it against the RFC 6068 grammar with `strict=True`; in both modes a decoded line break
  or NUL outside the body raises `MailtoError` instead of reaching a header value.
- Writing: `build` and `Mailto.to_uri` encode every field, write body line breaks as
  `%0D%0A` and refuse input that would not survive the trip (invalid addresses, controls
  outside the body, fields RFC 6068 section 3 says clients must ignore).
- `Mailto`, a frozen, hashable value with `recipients`, `header`, `header_all` and `safe`.
- `is_address` for the addr-spec form a `mailto:` URI may carry.
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

### Added

- A runnable example in the docstring of every public name, run as doctests.
- A guide, `GUIDE.md`, with the behaviour of every public name in detail.

## [0.2.0]

### Added

- `parse(uri, strict=True)` checks the RFC 6068 grammar and raises `MailtoError` with
  the offset of the first problem; `MailtoError` gains `reason` and `offset`.
- `is_address` tells whether a string is an addr-spec a `mailto:` URI may carry.
- `Mailto.recipients`, `header`, `header_all`, `safe` and `to_uri`.
- A `mailtourl` command (and `python -m mailtourl`) with `parse` and `build`.

### Changed (breaking)

- `Mailto` holds tuples instead of lists and `headers` is a tuple of `(name, value)`
  pairs instead of a dict; every argument but `to` is keyword-only.
- `build` raises `MailtoError` for input 0.1.0 wrote as is (see below), and body line
  breaks come out as `%0D%0A`.
- A decoded NUL or any line break `str.splitlines` knows, outside the body, raises
  `MailtoError` in every mode instead of reaching a header value. Field names are
  decoded and trimmed before they are classified, so an encoded or padded `bcc` lands in
  `bcc`, and in the default mode a name that is not a field name is dropped.

### Changed
- `parse` applies the URL Standard preprocessing (leading and trailing controls and
  spaces stripped, tabs and newlines removed) and ignores the fragment.
- The first `subject` and `body` win; repeated other fields are all kept.
- `Mailto` is frozen and hashable: tuples for recipients and ordered `(name, value)`
  pairs for `headers`.
- `build` writes body line breaks as `%0D%0A`, encodes `@` inside a quoted local part
  and `+` in field values, and refuses invalid addresses, controls outside the body,
  header names that are not field names, repeated headers, headers that have their own
  argument and the fields RFC 6068 section 3 says clients must ignore.

## [0.1.0]

- First release: `parse` and `build` for `mailto:` URIs per RFC 6068, covering
  `to`, `cc` and `bcc` recipients, `subject`, `body` and other header fields,
  with correct percent-encoding in both directions.
