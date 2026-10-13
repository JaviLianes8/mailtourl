# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
