# mailtourl 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to mailtourl. PyPI has no release of
mailtourl (`https://pypi.org/pypi/mailtourl/json` answered 404 on 2026-10-22), so there is
no upgrade path to check; the changes below are against `main` at 74305ea (0.2.0, never
published).

Progress:
- [x] Branch `release/1.0.0` created from `main` (74305ea)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: sources re-fetched live, reference implementations (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e, every Python on this PC (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] Merge and publish (item 17), left to the maintainer

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: five names, signatures and defaults kept from 0.2.0 and pinned by `tests/test_contract_api.py`; every behaviour change in CHANGELOG |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 11 doctests; README (4 blocks, 10 outputs) and GUIDE (7 blocks, 30 outputs) run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, consumer typing pinned by `tests/test_typing.py` |
| 5 | Typed, documented, bounded errors | PASS: `MailtoError` (a `ValueError`) with `reason` and `offset`, `TypeError` for wrong types, quoted input capped at 60 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: see Ground truth |
| 8 | Real e2e from the wheel | PASS: wheel installed in a throwaway venv, used from an empty folder, CLI by subprocess (script and `python -m`); no PyPI release to upgrade from |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS: see Fuzz and hostile input |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8.20 and 3.9.25 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge, verified comparison |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-22 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR from `release/1.0.0`; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: 42 author mutants, 40 killed at once, 2 survivors killed by new contracts |
| 19 | Five independent QA lenses | pending |

## Baseline on 0.2.0 (before any change)

`ruff format --check .`, `ruff check .`, `mypy --strict src tests` exit 0; `pytest` 383
passed, 1 skipped (the installed-wheel test, opt-in). Defects found by reading, then
reproduced:

- `Mailto.header(1)` and `Mailto.header_all(None)` raised `AttributeError`.
- Two strict-mode messages quoted a whole header field name: 100,053 and 100,058
  characters for a 100,000 character name; 60 lone surrogates gave a 401 character message.
- `Mailto` stored `str` subclasses as given, so a subclass with its own `__eq__` changed
  equality; `Mailto(None)` and `build(to=5)` raised Python's own "object is not iterable".
- `parse("   ")` reported offset 3 (the length) instead of 0.
- `Mailto` and `MailtoError` pickled under their private modules.
- `python -m mailtourl` ran the command on import, so doctest collection could not import it.
- No public docstring had a runnable example; the README linked LICENSE relatively; no GUIDE.
- `release.ps1` refused any upload once the name existed on PyPI (a second release could
  never go out).

## API review (item 1)

Kept: `parse(uri, *, strict=False)`, `build(to=None, *, cc, bcc, subject, body, headers)`,
`is_address(text)`, `Mailto` (fields `to`, `cc`, `bcc`, `subject`, `body`, `headers`;
`recipients`, `header`, `header_all`, `safe`, `to_uri`) and `MailtoError(message,
offset=None)` with `reason` and `offset`. Changed (all in CHANGELOG and GUIDE): the defects
above. The GUIDE states what SemVer covers: names, signatures, defaults, `Mailto` fields,
exception types, `reason`/`offset` and the CLI options, not message wording.

## Ground truth (item 7)

Fetched in this run on 2026-10-22 and compared byte for byte with
`tests/upstream/MANIFEST.json` (first fetched 2026-10-13; size and sha256 equal):

| Source | URL |
| --- | --- |
| RFC 6068 | https://www.rfc-editor.org/rfc/rfc6068.txt |
| RFC 3986 | https://www.rfc-editor.org/rfc/rfc3986.txt |
| RFC 5322 | https://www.rfc-editor.org/rfc/rfc5322.txt |
| RFC 6532 | https://www.rfc-editor.org/rfc/rfc6532.txt |
| WHATWG URL source | https://raw.githubusercontent.com/whatwg/url/fde3f74f063341a28d437216f75735b8b40128f5/url.bs |

Also fetched on 2026-10-22, for claims in the README (not shipped):
`https://www.rfc-editor.org/errata/rfc6068` (sha256 8574961f...27225f4): errata 7919
Verified (Technical, drops the `&`, `;`, `=` requirement in addresses), 4020 Verified
(Editorial, obs-NO-WS-CTL), 4706 Reported, 3491 Rejected. The PyPI simple index (920,171
names) for packages named with "mailto", their JSON metadata, and the `mailto-uri` 1.2.0
wheel (builder only, `urllib.parse.quote`, last upload 2019-06-12). Ruby
`https://docs.ruby-lang.org/en/master/URI/MailTo.html` and Android
`https://developer.android.com/reference/android/net/MailTo` answered 200; GitHub search
lists `swift-ietf/swift-rfc-6068`. The `parse_qsl` output quoted in the README is checked
by a test against the running interpreter.

Independent implementations run by the suite:

- Node.js v24.18.0 WHATWG `URL`: built URIs (401 seeded) pass through unchanged; 10
  tricky inputs read the same before and after the browser serialisation.
- Perl `URI::mailto` (URI 5.34, perl 5.42.2 of Git for Windows): 3,000 seeded built URIs
  and 15 RFC style examples decode to the same fields. Its source shows it reads `+` as a
  space outside the path, turns a path space into `+` and splits on `;`; the generator
  avoids those three.
- Python `email.headerregistry.Address`: every ASCII address `is_address` accepts among
  30,000 seeded candidates (more than 1,000 accepted) splits into the same local part and
  domain.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: 18,000 hostile URIs on three seeds through both modes (only
`MailtoError`, offsets inside the input, messages under 300 characters, no line break in a
single-line field, `safe()` keeps only addr-specs, strict results equal default results,
anything that rebuilds reads back strictly) and 8,000 random builder inputs (a strict,
printable ASCII URI or `MailtoError`). `tests/test_hostile.py`: 20 error paths with 100,000
character inputs stay under 300 characters; 18 shapes timed at 4,000 and 64,000 units grow
linearly (bound 64x for 16x input). Free-threaded 3.14.2t runs the whole suite.

## Packaging, e2e and interpreters (items 8, 10, 13, 14)

From a fresh clone of `release/1.0.0` at 5dd47a6 on this PC: wheel and sdist built,
`twine check --strict` PASSED for both. Wheel: the package, `py.typed`, METADATA,
entry point, `licenses/LICENSE`; no tests or scripts. Sdist: sources, tests,
`tests/upstream/MANIFEST.json` only (no fetched file), README, GUIDE, CHANGELOG,
CONTRIBUTING, LICENSE, scripts; no `IMPROVEMENTS-round*` or `CERT-1.0-*`. The sdist test
suite, with `src` removed so it imports the installed wheel, passed 471, skipped 1 (the
opt-in e2e) on each of CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, with
the fetched sources, Node.js and Perl present. 3.8.20 and 3.9.25 refuse the wheel. The e2e
test (`MAILTOURL_E2E=1`) builds, checks metadata (Production/Stable, no runtime
requirement), runs the doctests of the installed package and drives the CLI.

## Author mutation round (item 18)

Each mutant applied alone to a clean copy, full suite with fetched sources, Node.js and
Perl, on Elena's PC (`-x`, first failing test shown).

| Id | Mutation | Killed by |
| --- | --- | --- |
| M01 | NEL dropped from the line breaks refused outside the body | test_review_fixes::test_every_line_break_in_a_header_is_injection |
| M02 | `@` dropped from some-delims | test_build::test_header_names_keep_every_printable_ascii_but_colon |
| M03 | `+` left raw in built field values | doctest `build` |
| M04 | `,` left raw inside built addresses | test_build::test_addresses_encode_comma_and_the_sub_delims_the_rfc_named |
| M05 | off by one: U+FDEF noncharacter accepted | survived; killed by test_contract_edges::test_noncharacters_are_refused_in_addresses |
| M06 | off by one: DEL not a control | test_security::test_build_refuses_controls_in_subject_and_headers |
| M07 | bare whitespace allowed in a quoted local part | test_strict::test_invalid_uris_raise_with_offset |
| M08 | domain literal accepts backslash and controls | test_address::test_invalid_addresses |
| M09 | empty dot-atom part accepted | test_address::test_invalid_addresses |
| M10 | lone CR in the body not turned into CRLF | test_browser::test_built_uris_pass_through_the_url_class_unchanged |
| M11 | controls allowed in built fields | doctest `build` |
| M12 | repeated header allowed in build | test_build::test_build_refuses_a_repeated_header |
| M13 | dedicated fields accepted through headers | test_build::test_build_refuses_a_header_owned_by_a_dedicated_argument |
| M14 | fields joined with `;` | doctest `build` |
| M15 | cc and bcc swapped | doctest `build` |
| M16 | ASCII needing an escape accepted in a domain | test_build::test_build_refuses_a_domain_char_that_would_need_an_ascii_escape |
| M17 | strict accepts a one-digit escape | test_mutation_gaps::test_every_escape_needs_two_hex_digits |
| M18 | strict decodes Latin-1 | test_build::test_build_output_is_strictly_valid_and_reads_back |
| M19 | default field name not trimmed before classification | test_review_fixes::test_unicode_padding_cannot_hide_a_bcc |
| M20 | last subject wins | test_docs::test_every_guide_example_runs_and_prints_its_comment |
| M21 | fragment kept | doctest `parse` |
| M22 | off by one: recipient offsets drift | test_strict::test_invalid_uris_raise_with_offset |
| M23 | strict allows a repeated field | test_docs::test_every_guide_example_runs_and_prints_its_comment |
| M24 | space not stripped around the URI | doctest `parse` |
| M25 | CR not removed by browser preprocessing | test_browser::test_the_lenient_reading_agrees_with_the_browser_serialisation |
| M26 | injection guard skips the first character | doctest `MailtoError` |
| M27 | strict body accepts a bare LF | test_docs::test_every_guide_example_runs_and_prints_its_comment |
| M28 | strict accepts an encoded `@` before the domain | test_fuzz::test_random_input_raises_only_mailto_error_and_keeps_the_promises |
| M29 | strict accepts escaped ASCII 0x70 to 0x7F in a domain | test_mutation_gaps::test_an_escaped_tilde_in_a_domain_is_an_ascii_escape |
| M30 | off by one: injection offset | doctest `MailtoError` |
| M31 | `safe` keeps recipients that are not addr-specs | doctest `Mailto.safe` |
| M32 | header lookup becomes case-sensitive | doctest `Mailto.header` |
| M33 | recipients in the wrong order | doctest `Mailto.recipients` |
| M34 | pickling drops the offset | test_contract_api::test_public_classes_live_and_pickle_under_the_package_name |
| M35 | messages quote up to 6,000 characters | test_hostile::test_error_messages_stay_short_for_huge_input |
| M36 | `MIME-*` fields not refused | test_security::test_build_refuses_fields_rfc_6068_says_clients_must_ignore |
| M37 | `safe` drops keywords by default | test_cli::test_parse_safe_drops_unsafe_headers |
| M38 | CLI exits 1 on invalid input | test_cli::test_parse_strict_reports_the_error_and_exits_2 |
| M39 | `--safe` ignored | test_cli::test_parse_safe_drops_unsafe_headers |
| M40 | `str` subclasses stored as given | test_contract_api::test_the_constructor_stores_tuples_of_plain_str |
| M41 | blank input error offset at the end | survived; killed by test_contract_edges::test_blank_input_reports_offset_zero |
| M42 | `+` read as a space | doctest `parse` |

## Gates (item 15)

At ac88d89 on Elena's PC from a fresh clone, CPython 3.14.2, ruff 0.17.1, with the
fetched sources, Node.js, Perl and `MAILTOURL_E2E=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (501 passed,
none skipped) each exit 0.

## QA lenses (item 19) and independent review (item 16)

Pending: run after this report on fresh agents.
