# mailtourl

Parse and build `mailto:` URIs per RFC 6068 with correct percent-encoding.

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
# "mailto:jane@example.com,jack@example.com?cc=team@example.com"
# "&subject=Re:%20caf%C3%A9%20%26%20tea&body=Hello%0AWorld"

mail = parse(uri)
mail.to  # ["jane@example.com", "jack@example.com"]
mail.cc  # ["team@example.com"]
mail.subject  # "Re: café & tea"
mail.body  # "Hello\nWorld"
```

`parse` reads recipients from the path and from `to`, `cc` and `bcc` fields,
decodes `subject` and `body`, and keeps any other header field in `headers`. It
is case-insensitive for the scheme and the known field names, accepts an empty
`mailto:`, and tolerates a query segment that has no value. It raises
`MailtoError` when the string is not a `mailto:` URI.

`build` accepts one address or an iterable for each recipient slot, percent-encodes
every field, and returns the URI. A round trip through `build` and `parse`
preserves every field.

## Why

The standard library does not model `mailto:` semantics: `urllib.parse` treats the
whole address list as an opaque path and never reads the `to`, `cc`, `bcc`,
`subject` or `body` fields, so the recipient split and the field percent-encoding
are left to the caller. Other languages ship this (`URI::MailTo` in Ruby,
`swift-rfc-6068`, the Android `MailTo` class), but Python has no maintained
equivalent. `mailtourl` fills that gap with a small, typed, zero-dependency codec
that parses and builds in both directions.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
