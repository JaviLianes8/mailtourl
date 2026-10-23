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
- [x] Five QA lenses report PASS (item 19)
- [x] Independent reviewer reports PASS (item 16)
- [ ] Merge and publish (item 17), left to the maintainer

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: five names, signatures and defaults kept from 0.2.0 and pinned by `tests/test_contract_api.py`; every behaviour change in CHANGELOG |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 11 doctests, the five public names' examples also in a fresh namespace; README (4 blocks, 10 outputs) and GUIDE (7 blocks, 32 outputs) run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, consumer typing pinned by `tests/test_typing.py` |
| 5 | Typed, documented, bounded errors | PASS: `MailtoError` (a `ValueError`) with `reason` and `offset`, `TypeError` for wrong types, quoted input capped at 60 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: see Ground truth |
| 8 | Real e2e from the wheel | PASS: wheel installed in a throwaway venv, used from an empty folder, CLI by subprocess (script and `python -m`); no PyPI release to upgrade from |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS: see Fuzz and hostile input |
| 10 | Supported Pythons | PASS at 2224141, again at 3407455: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8.20 and 3.9.25 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge, verified comparison |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-22 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | PASS: round 1 at 3407455, every item PASS (see Independent review) |
| 17 | PR and trace guard | PASS for this branch: PR #3 from `release/1.0.0` to `main`, trace guard clean; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: 42 author mutants, 40 killed at once, 2 survivors killed by new contracts |
| 19 | Five independent QA lenses | PASS: all five lenses report PASS (see QA verdicts) |

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
`recipients`, `header`, `header_all`, `safe`, `to_uri`) and `MailtoError(reason,
offset=None)` with `reason` and `offset` (the first parameter was `message` until QA
round 1, see below). Changed (all in CHANGELOG and GUIDE): the defects
above. The GUIDE states what SemVer covers: names, signatures, defaults, `Mailto` fields,
exception types, `reason`/`offset` and the command line (options, the JSON that `parse`
prints, exit statuses), not message wording.

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
  space outside the path, turns a path space into `+` and splits on `;`. The generator
  avoids the last two; since QA round 2 it puts `+` in local parts (lens b B2-1), which
  `build` must write as `%2B` in `cc` and `bcc` for Perl to agree.
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
linearly (bound 64x for 16x input). Free-threaded 3.14.2t runs the whole suite (at
2224141, see QA round 2).

## Packaging, e2e and interpreters (items 8, 10, 13, 14)

From a fresh clone of `release/1.0.0` at 2224141 on this PC (QA round 2; first run at
5dd47a6): wheel and sdist built,
`twine check --strict` PASSED for both. Wheel: the package, `py.typed`, METADATA,
entry point, `licenses/LICENSE`; no tests or scripts. Sdist: sources, tests,
`tests/upstream/MANIFEST.json` only (no fetched file), README, GUIDE, CHANGELOG,
CONTRIBUTING, LICENSE, scripts; no `IMPROVEMENTS-round*` or `CERT-1.0-*`. The sdist test
suite, with `src` removed so it imports the installed wheel, passed 657, skipped 1 (the
opt-in e2e), and the sdist tree with `MAILTOURL_E2E=1` passed 669, none skipped, on each
of CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, with the fetched
sources, Node.js and Perl present. 3.8.20 and 3.9.25 refuse the wheel. The e2e
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

### Round 1 (QA lenses a to e on b488ff9)

Every finding was fixed; none is disputed. Each behaviour bug got a contract test first,
run against b488ff9 to see it fail, then the fix: 80 of the 107 new cases fail there (one
only because the module it tests is new); the 27 that pass are lens e's mutation-gap
contracts, which pass on correct code by design, and cases that were already right. Fix
commits: 7c6da55 (code and tests), 1e47fbc (docs), ab4ddb5 (installed-package e2e).

| Lens | Id | Severity | Finding | Resolution |
| --- | --- | --- | --- | --- |
| a | M1 | medium | `is_address` accepted a domain holding an ASCII character that needs an escape (`/`, `#`, `&`, ...), which no URI can carry | `is_address` applies the domain rule of `build` (`_address.check_domain`, shared): true exactly when `build` can write the address; `tests/test_writable.py` (per character, plus 20,000 seeded candidates agreeing with `build`) |
| a | M2 | medium | `safe()` did not make a value buildable | `safe()` now guarantees it: drops a subject or body with a control `build` refuses, allowed headers `build` refuses, repeats of an allowed name (first wins); `to_uri` docstring and docs state what it refuses in either mode; `tests/test_writable.py` (cases plus 12,000 seeded default-mode reads, each `safe().to_uri()` re-read strictly) |
| a | L1 | low | `Mailto` refused `None` where `build` takes it | `Mailto` takes `None` for `to`, `cc`, `bcc`, `headers`, now their defaults |
| a | L2 | low | `build`, `parse`, `is_address` named private modules and aliases | `__module__` set to `mailtourl`; `build` signature spells out its types; `test_public_functions_live_under_the_package_name` (pickle, pydoc) |
| a | L3 | low | `MailtoError` example missed an import | every public docstring example imports what it uses; `test_every_public_docstring_example_runs_in_a_fresh_namespace` |
| a | L4 | low | constructor parameter `message` vs attribute `reason` | renamed to `reason`; `test_mailto_error_takes_its_reason_by_name` |
| a | L5 | low | README mischaracterised the other "mailto" packages | reworded after re-fetching the PyPI simple index and the JSON of all 22 names on 2026-10-22 |
| a | L6 | low | old CHANGELOG sections not Keep a Changelog | dated 0.2.0 (2026-10-13) and 0.1.0 (2026-10-12) from git, standard categories with `BREAKING:` items, commit link references; the 1.0.0 "Stable" heading became prose |
| b | F1 | medium | default-mode offset wrong after bytes that are not UTF-8 | new `_positions.char_starts` walks the UTF-8 maximal subparts that the `replace` handler turns into U+FFFD; `tests/test_offsets.py` (21 fixed cases, 4,000 seeded injections, 20,000-case oracle against `urllib.parse.unquote` of every prefix) |
| b | F4 | medium | strict accepted an encoded `@` separator after a quoted local part | separator located in the decoded address and required raw at its mapped position; error points at it |
| b | F5 | low | strict "not UTF-8" offset at the field start | `UnicodeDecodeError.start` mapped back to its escape (`_positions.byte_position`) |
| b | F2 | low | `is_address` Unicode exclusions undocumented, interpreter-dependent | GUIDE lists the categories, the joiners, the noncharacters and the `unicodedata` version dependence; docstring and README point to it |
| b | F3 | low | default mode does not normalise `/` paths as a browser does | claim narrowed in README, GUIDE and `parse` docstring to the cleaning applied; the path normalisation listed under "Not covered" |
| b | F6 | low | CLI stripped all whitespace from stdin | one trailing line ending only; `tests/test_cli_stdin.py` |
| c | C-3 | medium | same as b F1 | as b F1 |
| c | C-1 | medium | CLI traceback on stdin bytes that are not UTF-8 | stdin read as bytes and decoded as UTF-8; failure is `MailtoError`, exit 2 |
| c | C-2 | low | Windows stdin decoded with the code page | same fix; in-process tests with cp1252 and ASCII text streams, a subprocess test and the installed-wheel e2e |
| c | C-4 | low | `build` trusted `str` subclasses | `build`, `parse`, `is_address` coerce with `str.__str__` (`_chars.plain`); `test_build_reads_a_str_subclass_as_plain_str` |
| c | C-5 | low | default mode used about 50x the input in memory | no per-character index list: cleaning with one regex pass, index mapped back only on error. Peaks now 3.0x (subject), 7.5x (recipients), against strict 5.0x and 11.2x; the peak for a body of `%41` is `urllib.parse.unquote_to_bytes` itself, equal in both modes (78.2x on 3.10.19 and 3.11.5, 21.6x on 3.12.12 to 3.14.2, 27.0x on 3.14.2t; round 2 d F3); pinned by two tracemalloc tests |
| d | F1 | medium | same as c C-1/C-2, BOM refused | BOM skipped; e2e pipes UTF-8 and a BOM-prefixed URI into the installed script and `python -m` |
| e | F1, F2 | medium, low | offsets after bytes that are not UTF-8; the end-of-input remap branch | as b F1; the branch is gone (only blank input maps to 0, pinned by `test_blank_input_reports_offset_zero`) |
| e | F3 to F8 | medium, low | survivors C13, B5, W17, W33, E3, E1, W14 | one contract each in `tests/test_api_freeze.py` and `tests/test_cli_stdin.py` |
| e | F9 | low | survivor L7 (`except ValueError`) | undecodable stdin now exits 2 with one line, pinned in process and by subprocess; L7 is now an equivalent mutant: no `ValueError` other than `MailtoError` reaches that handler |

Mutants re-applied to the fixed tree, one at a time, against the new tests:

| Mutant | Result |
| --- | --- |
| C13 `is_vchar` 33..127 | killed: `test_a_quoted_pair_cannot_escape_a_control[]` |
| B5 duplicate check by `name` | killed: `test_build_refuses_a_header_repeated_in_any_case` |
| W17 `PCHAR` for recipient fields | killed: `test_strict_refuses_a_raw_equals_sign_in_a_recipient_field` |
| W33 `dict(mail.headers)` in the CLI | killed: `test_repeated_headers_all_reach_the_json` |
| E3 `if not offset` | killed: `test_the_error_for_offset_zero_still_names_the_offset` |
| E1 `quoted` `<` | killed: `test_messages_quote_sixty_characters_whole_and_cut_sixty_one` |
| W14 field name `shown` `<` | killed: `test_strict_messages_name_a_field_of_sixty_characters_whole` |
| L7 `except ValueError` | equivalent (see e F9) |
| blank input offset at `begin` | killed: `test_blank_input_reports_offset_zero` |
| separator check back to `"@" not in raw` | killed: `test_strict_refuses_an_encoded_separator_and_points_at_it` |
| strict UTF-8 offset at field start | killed: `test_strict_points_at_the_escape_that_is_not_utf_8` |
| E0 second-byte range widened | killed: `test_lenient_offsets_survive_bytes_that_are_not_utf_8[%E0%80%0A]` |
| `safe()` keeps repeated names | killed: `test_safe_keeps_only_what_to_uri_can_write` |
| `is_address` without the domain rule | killed: `test_a_domain_char_that_needs_an_ascii_escape_is_not_an_address` |
| stdin strips all trailing whitespace | killed: `test_strict_input_keeps_its_padding_on_standard_input` |

Gates at ab4ddb5 on Elena's PC from a bundle of the branch, CPython 3.14.2 in a fresh
venv, fetched sources, Node.js, Perl and `MAILTOURL_E2E=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (608 passed,
none skipped) each exit 0. The decoder mapping and the offset injection check also ran
clean on CPython 3.10.19, 3.11.5, 3.12.12 and 3.14.2t on this PC.

### Round 2 (QA lenses a to e on 78646da)

Every finding was fixed; none is disputed. Each behaviour bug got a contract test first,
run against 78646da to see it fail, then the fix: of the new and changed cases
(`tests/test_first_offender.py`, `tests/test_cli_streams.py`,
`tests/test_plus_and_pairs.py`, the memory case in `tests/test_api_freeze.py`, `+` in
the Perl generator of `tests/test_oracles.py`, `tests/test_roundtrip.py` and the
updated offsets of `tests/test_strict.py`), 69 fail on 78646da; those that pass there
are lens e's mutation-gap contracts, right on both trees by design, and unchanged cases.
Fix commits: f58e53b (code and tests), 2224141 (README, GUIDE, CHANGELOG).

| Lens | Id | Severity | Finding | Resolution |
| --- | --- | --- | --- | --- |
| a | F1 | medium | strict offset of a malformed address or field name pointed at its start; the GUIDE example contradicted the rule | fixed in code (also b B2-3): `split_address` raises with the index of the fault, mapped back through the escapes; field names report their first bad character; the GUIDE example now prints 8 |
| b | B2-3 | low | same as a F1, seven more shapes | as a F1; the seven shapes are pinned in `tests/test_first_offender.py`; 19 offsets of `tests/test_strict.py` moved from the start of the part to the character |
| b | B2-2 | low | when a part breaks several rules, the first rule checked won, not the first offender in the text (fragment, raw characters, escapes, missing `=`) | strict mode runs every rule of a part (raw characters and escapes in one pass, UTF-8, injection, controls, address, field name, missing `=`) and raises the error with the lowest offset (on a tie, the raw-character rule); the fragment is checked after the parts; the address check takes the lowest of its grammar, the encoded `@` and an ASCII escape in the domain |
| a | F2 | low | `--safe` help described less than `Mailto.safe()` does | help: "apply Mailto.safe(): keep only what is safe in general and to_uri writes", pinned |
| a | F3 | low | GUIDE and CHANGELOG named different command line promises | both say: the options, the JSON `parse` prints (keys, list shapes, ASCII) and the exit statuses (0, 2) follow SemVer |
| a | F4 | low | README said "controls" for C0 controls | "C0 controls" in both places |
| a | F5 | low | `safe(allow=None)` silently kept no header; the `str` case undocumented | `None` raises `TypeError`; docstring and GUIDE say `allow` is one name as a `str` or an iterable of names; CHANGELOG |
| b | B2-1 | medium | `build` left `+` raw in `cc` and `bcc` addresses, which Perl `URI::mailto` and `parse_qsl` read as a space | `+` written as `%2B` in query addresses; a domain name cannot hold it either way (RFC 6068 allows no ASCII escape there), so `is_address` refuses a `+` in a domain name, as it already did `&` and `=`; the Perl differential now includes `+`, the round trip asserts no raw `+` in the query, `parse_qsl` contract |
| b | B2-4 | low | docs said controls are refused only outside the body | README (two places), `build` docstring and GUIDE strict list: C0 and C1 controls but tab are refused in every field; the body also takes CRLF line breaks |
| c | F1 | low | traceback and exit 1 with no standard input or output | exit 2 with "no standard input" or "no standard output"; without standard error the reason never falls back to standard output; four contracts |
| c | F2 | low | the `--header` error echoed the argument, value included; strict `parse` and `build` quoted a malformed field name whole | "--header expects NAME=VALUE" without the argument; a field name is reported by the character at fault in `build` and strict `parse` (`_headers.name_fault`) |
| c | F3 | low | `build` and `Mailto` read a lying pair differently, `Mailto` raised `ValueError` | both read the pair from what the tuple or list holds (`_headers.read_pair`), only `TypeError`; contracts with tuple and list subclasses that lie in `__iter__`, `__getitem__` and `__len__` |
| d | F1 | medium | the `tabs` memory contract failed on free-threaded 3.14.2t (16.96x the input) | the browser cleaning uses `str.replace` instead of a regex substitution and its list of pieces: 2.00x on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t (was 9.95x and 16.96x); new contract below 4x for tab, LF and CRLF; full suite green on 3.14.2t (below) |
| d | F2 | low | the interpreter claims of this report described 5dd47a6 | matrix rerun at 2224141; sections Packaging and Fuzz updated |
| d | F3 | low | the 21.6x of round 1 C-5 holds only on 3.12 and later | the C-5 row names the interpreters: 78.2x on 3.10.19 and 3.11.5, 21.6x on 3.12.12, 3.13.2 and 3.14.2, 27.0x on 3.14.2t, equal in both modes on each |
| e | R2-1, R2-2 | low | survivors N4, N10: UTF-8 lead boundaries C0, C1 and F5 to F7 | lenient offset contracts, killed |
| e | R2-3 | low | survivor N35: strict body offsets through escapes | contracts, killed |
| e | R2-4 | low | survivor N39: a removed tab or newline right before the problem | contracts, killed |
| e | R2-5 | low | survivor N74: byte number after a BOM | "at byte 19" contract, killed |
| e | R2-6 | low | survivor N79: an empty URI argument replaced by stdin | contract, killed |
| e | R2-equiv | low | M10, P19, L7, N18 equivalent | M10, P19 and L7 stay equivalent as proved; the `position` fallback of N18 is now reachable (an unterminated quoted local part reports the end of the address) and N18 is killed |

Mutants applied to the fixed tree, one at a time:

| Mutant | Result |
| --- | --- |
| N4, N10 (lens e) | killed: `test_lenient_offsets_count_what_was_decoded_or_removed` |
| N35 (lens e) | killed: `test_strict_points_at_the_first_offending_character[mailto:?body=%41%00-16]` |
| N39 (lens e) | killed: `test_lenient_offsets_count_what_was_decoded_or_removed` (tab before `%0A`) |
| N74 (lens e) | killed: `test_the_bad_byte_is_counted_from_the_start_of_the_input_bom_included` |
| N79 (lens e) | killed: `test_an_empty_uri_argument_is_parsed_not_replaced_by_stdin` |
| N18 (lens e), and the fallback off by one | killed: `test_strict_points_at_the_first_offending_character[mailto:%22ab@x.example-22]` |
| `read_part` raises the first rule's error | killed: `[mailto:a@x.example?subject=%FF<-27]` |
| `check_address` raises the first rule's error | killed: `[mailto:a@x%2E%2Eexample-10]` |
| address errors at the start of the address | killed: `[mailto:j%20d@x.example-8]` |
| `_separator` skips one character after a backslash | killed: `test_random_values_round_trip_through_build_and_both_parsers` |
| missing `@` at offset 0; literal and trailing-dot offsets off by one | killed: `[mailto:abc-10]`, `[mailto:a@%5B1.2%5Cx%5D-15]`, `[mailto:a.@x.example-9]` |
| `read_pair` iterates the tuple or the list, or trusts `len` | killed: `test_build_and_mailto_read_a_pair_from_what_it_holds[pair0]` and `[pair2]`, `test_a_pair_that_lies_about_its_length_is_a_type_error_in_both` |
| `+` raw in query addresses (two ways); `+` allowed in a domain name | killed: `test_a_plus_in_a_cc_or_bcc_address_is_encoded`, `test_a_plus_in_a_domain_name_cannot_be_written` |
| CR left in the cleaned text | killed: `test_removing_tabs_and_newlines_costs_at_most_a_copy[crlf]` |
| no stdin, stdout or stderr check in the command | killed: `test_no_standard_input_exits_2_with_one_line`, `test_no_standard_output_exits_2_with_one_line`, `test_without_standard_error_the_reason_never_lands_on_standard_output` |
| `safe(allow=None)` accepted | killed: `test_safe_takes_no_none_for_its_allow_list` |
| the missing `=` error listed before the name rules | equivalent: it sits at the end of the segment, after every other error of the name |

Gates at 2224141 from a fresh clone of the pushed branch on this PC (the interpreters
live only here; turn `pc/5`): wheel and sdist built, `twine check --strict` passed. On
each of CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, the sdist tree
with the fetched sources, Node.js, Perl and `MAILTOURL_E2E=1` passed 669 (none skipped),
and the suite against the installed wheel (`src` removed) passed 657, skipped 1 (the
opt-in e2e). `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 at the same commit.

### Round 3 (re-verification of round 2 by lenses c and e on 07e06f7)

Lens c re-verified its round 2 findings F1 to F3 as fixed and its sweep (60,000 seeded
strict and default-mode reads, the `+` round trip, `is_address`, `build` and `safe()`
agreement, 29 scaling shapes, CLI streams) came back clean but for F4. Lens e re-verified
R2-1 to R2-6 as fixed and N18 as killed; M10, P19 and L7 stay equivalent; of its 40 new
mutants, 38 were killed and 2 survived. Every finding was fixed; none is disputed. The
new and changed cases of `tests/test_first_offender.py`, `tests/test_build.py` and
`tests/test_strict.py` were run against 07e06f7: the 7 domain literal cases fail there
(3 strict offsets, 3 `build` reasons, the updated row of `tests/test_strict.py`); the 6
offset cases for the two survivors pass there, as mutation-gap contracts do.

| Lens | Id | Severity | Finding | Resolution |
| --- | --- | --- | --- | --- |
| c | F4 | low | a domain literal missing its `]` or followed by more text was reported at its opening `[` as "character '[' not allowed in domain" | `split_address` reads a domain that starts with `[` as a literal up to the first `]`: "unterminated domain literal" at the end of the address, "text after the domain literal" at the first character after the `]`, any other character outside dtext where it stands; GUIDE lists a closing `]` among the missing things, CHANGELOG under Fixed; three strict offsets and three `build` reasons pinned, the old row `mailto:a@%5B1.2.3.4` moved from 9 to 19 |
| e | R3-1 | low | survivor X9: `local = text[:at]` in `split_address` | strict offsets `mailto:ab%3C` 9, `mailto:ab%20` 9, `mailto:a.b%3C` 10 |
| e | R3-2 | low | survivor X38: `offset + fault[1]` in `check_name` | strict offsets `mailto:?%41%3A=1` 11, `mailto:?%41b%20=1` 12, `mailto:a@x.example?X-%41%3A=1` 24 |

Mutants applied to the fixed tree, one at a time, against `tests/test_first_offender.py`,
`tests/test_build.py` and `tests/test_strict.py`:

| Mutant | Result |
| --- | --- |
| X9 `local = text[:at]` (lens e) | killed: `[mailto:ab%3C-9]` |
| X38 `offset + fault[1]` (lens e) | killed: `[mailto:?%41%3A=1-11]` |
| text after the `]` tested with `index + 2` | killed: `[mailto:a@%5B192.0.2.1%5Dx-24]` |
| text after the `]` reported at the `]` | killed: `[mailto:a@%5B192.0.2.1%5Dx-24]` |
| unterminated literal reported one before the end | killed: `[mailto:?cc=a@%5B192.0.2.1-25]` |
| `]` never closes the literal | killed: `[mailto:a@%5B192.0.2.1%5Dx-24]` |
| the closing `]` does not stop the scan | killed: `test_a_domain_literal_has_its_brackets_encoded` |

Fix commit: 1ead1ea (code, tests, GUIDE, CHANGELOG). Gates at 1ead1ea: `ruff format
--check .`, `ruff check .`, `mypy --strict src` and `mypy --strict src tests` exit 0 on
this PC; `pytest` from an archive of the commit on Elena's PC (turn `elena/5`), CPython
3.14.2 in a fresh venv, fetched sources, Node.js, Perl and `MAILTOURL_E2E=1`: 681 passed,
none skipped.

### Round 4 (re-verification of round 3 by lenses c and e on 6f60ae1)

Lens c re-verified F4 as fixed on CPython 3.13.2 and 3.11.5, and its sweep (36 probes and
20,000 seeded cases on seed 20261023: literal offsets against an independent oracle,
`is_address` and `build` agreement, the strict round trip, 9 scaling shapes, odd types,
the command's exits) came back clean but for one finding, present since 07e06f7. Lens e
re-verified R3-1 and R3-2 as fixed; of its 30 new mutants on the domain literal code, 28
were killed and 2 survived. Every finding was fixed; none is disputed. The 9 strict
offsets and 8 reasons of the lens c finding fail on 6f60ae1; the 5 cases for the two
survivors pass there, as mutation-gap contracts do.

| Lens | Id | Severity | Finding | Resolution |
| --- | --- | --- | --- | --- |
| c | R3-1 | low | in strict mode, bytes that are not UTF-8 skipped every check of the address, field name or value holding them, so a later bad byte was reported in place of an earlier offender (`mailto:a@%5B1%5Dx%FF` at 17 instead of "text after the domain literal" at 16) | `read_part` still runs the checks when the bytes are not UTF-8, on the value with each bad part replaced, and keeps what they find before the first bad byte; a tie goes to the UTF-8 error. The nine URIs pinned in `tests/test_first_offender.py` with their offsets, eight with their reasons, and five ties where the UTF-8 error wins; CHANGELOG under Fixed, GUIDE on offsets |
| e | R4-1 | low | survivor Y2: `domain.startswith("[") and len(domain) > 1` in `split_address` | strict offset `mailto:a@%5B` 12 and `build("a@[")` "unterminated domain literal" |
| e | R4-2 | low | survivor Y29: `enumerate(domain[1:].rstrip(), 1)` in `_check_literal` | strict offsets `mailto:a@%5B1.2%20` 15 and `mailto:a@%5B1.2%09` 15, and `build("a@[1.2 ")` naming the space |

Mutants applied to the fixed tree, one at a time, against `tests/test_first_offender.py`
and `tests/test_build.py`:

| Mutant | Result |
| --- | --- |
| Y2 `domain.startswith("[") and len(domain) > 1` (lens e) | killed: `[mailto:a@%5B-12]`, `[a@[-unterminated domain literal]` |
| Y29 `enumerate(domain[1:].rstrip(), 1)` (lens e) | killed: `[mailto:a@%5B1.2%20-15]`, `[mailto:a@%5B1.2%09-15]`, `[a@[1.2 -...]` |
| checks skipped when the bytes are not UTF-8 (the code before the fix) | killed: 9 offset and 8 reason cases |

The lens c probe `utf8_hides.py` reports 0 mismatches out of 9 on the fixed tree.

Fix commit: 0fa30f9 (code, tests, GUIDE, CHANGELOG). Gates at 0fa30f9: `ruff format
--check .`, `ruff check .`, `mypy --strict src` and `mypy --strict src tests` exit 0 on
this PC; `pytest` from an archive of the commit on Elena's PC (turn `elena/2`), CPython
3.14.2 in a fresh venv, fetched sources, Node.js, Perl and `MAILTOURL_E2E=1`: 709 tests, exit
0, none skipped.

### Round 5 (re-verification of round 4 by lens e on 8128ef4)

Lens e re-verified R4-1 and R4-2 as fixed (Y2 and Y29 killed). Of its 25 new mutants on
`read_part` and its check loop, 18 were killed (counting Y2 and Y29) and 9 survived: Z2
(`< bad` to `<= bad`) and Z5 (the filter on the early errors removed) are equivalent, as
a differential run on 6,013 seeded inputs showed, and the other 7 gave four findings, all
mutation gaps with no behaviour change. Every finding was fixed; none is disputed. The new
cases pass on 8128ef4, as mutation-gap contracts do.

| Lens | Id | Severity | Finding | Resolution |
| --- | --- | --- | --- | --- |
| e | R5-F1 | low | survivor Z23: the checks skipped on a part with bad bytes whenever a raw character already failed | strict offset `mailto:a%20b<@x%FF` 8 |
| e | R5-F2 | low | survivor Z25: only the first check's early error kept on a part with bad bytes | strict offset `mailto:a%20b%0A@x%FF` 8 |
| e | R5-F3 | low | survivors Z10, Z12, Z14: the bad parts dropped, turned into a line feed, or the value cut at the first one before the checks read it | strict offsets `mailto:%22a%5C%FF` 14, `mailto:?body=%0D%FF` 13, `mailto:?body=%0D%FF%0A` 13 |
| e | R5-F4 | low | survivors Z11, Z13: each bad part read as `?` or a backslash instead of U+FFFD, visible only in the value a reason quotes | `parse("mailto:.%FF", strict=True)` pinned to its reason, which quotes the local part as a dot and U+FFFD, and offset 7, as `read_part` and the GUIDE promise |

Mutants applied to the fixed tree, one at a time, against `tests/test_first_offender.py`:

| Mutant | Result |
| --- | --- |
| Z23 `found = [] if errors[:-1] else _run(...)` | killed: `[mailto:a%20b<@x%FF-8]` |
| Z25 `for early in found[:1]` | killed: `[mailto:a%20b%0A@x%FF-8]` |
| Z10 bad parts removed | killed: `[mailto:%22a%5C%FF-14]`, `[mailto:?body=%0D%FF%0A-13]`, the reason test |
| Z11 bad parts as `?` | killed: `test_a_reason_quotes_a_bad_part_as_the_replacement_character` |
| Z12 bad parts as a line feed | killed: `[mailto:%22a%5C%FF-14]`, `[mailto:?body=%0D%FF-13]`, `[mailto:?body=%0D%FF%0A-13]`, the reason test |
| Z13 bad parts as a backslash | killed: `test_a_reason_quotes_a_bad_part_as_the_replacement_character` |
| Z14 value cut at the first bad part | killed: `[mailto:%22a%5C%FF-14]`, the reason test |

Fix commits: ec08bb3 and 34214c9, which writes the replacement character in the reason
test as an escape (tests only; no behaviour change, so nothing new in the CHANGELOG).
Gates at 34214c9: `ruff format --check .`, `ruff check .`, `mypy --strict src` and `mypy
--strict src tests` exit 0 on this PC; `pytest` from an archive of the commit on Elena's
PC (turn `elena/4`), CPython 3.14.2 in a fresh venv, fetched sources, Node.js, Perl and
`MAILTOURL_E2E=1`: 715 tests, exit 0, none skipped.

### Disputed findings

None.

### QA verdicts

Lens e re-verified R5-F1 to R5-F4 as fixed on 3407455. Since lenses a, b and d gave
their verdicts at 07e06f7, `src` changed only in `_address.py` and `_strict.py` (the
domain literal and bad-byte offset fixes from lenses c and e, re-verified by those two
lenses); the independent review re-ran the interpreter matrix, packaging and e2e at
3407455. Report paths are relative to the local certification work folder, which is
not part of the repository.

| Lens | Rounds | Final verdict | Report | Commit |
| --- | --- | --- | --- | --- |
| a: API and docs | 2 | PASS | `lens-a-r2/probes` (`repro.py`, `docs.py`, `sweep.py`) and the round summary | 07e06f7 |
| b: correctness and ground truth | 2 | PASS | `lens-b-r2/REPORT.md` | 07e06f7 |
| c: adversarial and robustness | 4 | PASS | `lens-c-r4/probes` | 8128ef4 |
| d: packaging and real e2e | 2 | PASS | `lens-d-r2/out` (matrix logs for 3.10 to 3.14t, CLI sweep, twine, wheel and sdist lists) | 07e06f7 |
| e: contract strength | 5 | PASS | `lens-e-r5/results-r6.json` | 3407455 |

Lens a, round 2: the round 1 findings re-run as fixed; all 11 Python blocks in README and
GUIDE give the output the docs show; 30 doctests pass; a sweep of 40 probes (encoding of
`+` per field, domains holding `+`, 21 strict offset cases, header name errors, tuple and
list subclasses, the CLI with a malformed `--header` and with no stdin or stdout) found
nothing. Lens d, round 2: on CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t
the sdist tree with `MAILTOURL_E2E=1`, fetched sources, Node.js and Perl passed 669, none
skipped, and the installed wheel passed 657 with 1 skipped; the 3.14.2t memory peak is
2.0x with the GIL off and on; `twine check --strict`, `check-wheel-contents`, reproducible
bytes and the refusal of 3.9 all pass; a sweep of 40 API and CLI probes found nothing.

### Independent review

Round 1 on a fresh clone at 3407455 (PR #3 head), scored against the 19 items. Evidence
is in `review-r1/out`.

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API stable | PASS: signatures inspected; every behaviour change is in CHANGELOG 1.0.0 |
| 2 | `__all__` exact, no private imports | PASS: `__all__` is the five names, all with `__module__` `mailtourl`; README, GUIDE and CHANGELOG import only from `mailtourl` |
| 3 | Docstrings and doctests | PASS: every public name and `Mailto` method has an example; the doctests run in the gate |
| 4 | Typed end to end | PASS: `mypy --strict` on `src` (13 files) and `src tests` (42 files) exit 0; `py.typed` in the wheel; no `Any` in the public hints |
| 5 | Typed, bounded errors | PASS: `MailtoError` is a `ValueError` with `reason` and `offset`; a 200,000-character hostile input gives a message under 300 characters |
| 6 | Contract tests | PASS: `tests/test_contract_api.py` and `tests/test_contract.py` cover the surface; 6 independent mutants all killed |
| 7 | Real ground truth | PASS: all five MANIFEST URLs re-fetched on 2026-10-22, size and sha256 match; hand-written cases labelled |
| 8 | Real e2e | PASS: wheel installed in a throwaway venv on each of the six interpreters, used from an empty folder with `-I`, the API and the CLI (script and `python -m`) driven by subprocess; PyPI answers 404, so no upgrade path |
| 9 | Fuzz and hostile input | PASS: `test_fuzz` and `test_hostile` green in every run |
| 10 | Supported Pythons | PASS: sdist tests against the installed wheel passed 703 with 1 skip (the opt-in e2e) on CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t; 3.9.25 refused |
| 11 | README and `twine check` | PASS: `twine check --strict` for wheel and sdist; the README renders; links absolute; the comparison facts re-verified live. GUIDE and CHANGELOG links point to `main` and resolve once merged |
| 12 | Dated CHANGELOG section | PASS: `[1.0.0] - 2026-10-22` with a stable surface summary and Changed, Fixed, Added |
| 13 | pyproject | PASS: 1.0.0, Production/Stable, Python 3.10 to 3.14, MIT with License-File, four project URLs, 7 keywords, no runtime dependency |
| 14 | sdist and wheel contents | PASS: `check-wheel-contents` OK, a rebuild gives the identical wheel; the sdist ships only `MANIFEST.json` under `tests/upstream` |
| 15 | Gates | PASS: format, lint, `mypy --strict src` and `pytest` (715 passed, none skipped, with `MAILTOURL_E2E=1`, fetched sources, Node.js and Perl) each exit 0 |
| 16 | Independent review | PASS: this review; nothing posted to GitHub |
| 17 | PR and trace guard | PASS for this branch: tree, history, PR title and body clean, no em-dash, source files of 200 lines or fewer, branches `main` and `release/1.0.0` only; merge and publish left to the maintainer |
| 18 | Contracts bite | PASS: mutation tables recorded here; a spot round of 6 mutants (`+` raw in query addresses, cc and bcc swapped, case-sensitive `safe` allow list, quote cap 600, case-sensitive scheme, pickle dropping `offset`) killed 6 of 6 |
| 19 | Five QA lenses | PASS: all five lens artefacts exist and match the commits above |
