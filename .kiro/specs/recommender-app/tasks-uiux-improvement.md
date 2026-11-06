# Recommender app UI/UX improvement plan

Created 2026-10-25. Status: **proposal ready for implementation**. This plan
covers the movie discovery and rating experience, plus the live recommendation
display. It is independent of the backend architecture work tracked in
`tasks-improvement.md`.

## Goal

Make the recommender easy to explore and rate without requiring users to know
MovieLens item IDs or guess movie titles. Keep recommendations in the same
primary experience as rating, and make each newly computed result visibly
replace the prior result as soon as it arrives. This should demonstrate the
backend's responsive prediction path; database save confirmation remains a
separate status.

## Verified starting point

- The browser app is `examples/recommender/app.rbv`.
- It already requests `GET /movies`, but `server_api.bv` currently returns only
  item IDs; the UI renders these as a long string of numbers.
- Recommendations arrive over the existing live channel. The browser currently
  displays entries as `Movie N` in a separate section after the rating panel.
- MovieLens-100k `u.item` is available at `C:\Users\wotto\AutAI\ml-100k\u.item`.
  Its movie ID field corresponds to the 1-based IDs in `u.data`; the app and
  persisted ratings use 0-based item IDs internally.
- `u.item` is pipe-delimited and contains titles plus release/video dates, IMDb
  and TMDb URLs, and genre flags. The first delivery needs only ID and title.
- U01 inspection (2026-10-25): the supplied file has exactly 1,682 rows, IDs
  1..1682 in order, and nonempty titles. Its bytes are ISO-8859-1/Latin-1, not
  valid UTF-8; the parser must convert title code points to UTF-8 before JSON
  encoding. Follow the existing `UDATA_PATH` convention with `UITEM_PATH`
  (default `u.item`) so deployment supplies the data locally without copying
  the MovieLens file into the repository.

## Proposed user experience

1. **Browse and search the catalogue.** Show a useful first page of available
   titles immediately. A title search filters the same catalogue as the user
   types, so users can browse when they do not know what to search for and can
   narrow results when they do. Provide previous/next controls and a visible
   result count/page indicator. Search matches title text without case
   sensitivity; an empty query restores the browsable catalogue.
2. **Choose a film and rate it.** Each result has a clear selection/rating
   action. Show the selected title beside five accessible 1–5 rating choices
   and a submit action. Avoid exposing numeric item IDs in the normal flow.
3. **Show feedback and save state separately.** Immediately show the accepted
   rating as pending and keep the existing truthful saved/failed/retry states.
   A database save confirmation changes only the save indicator.
4. **Keep recommendations in the same primary view.** Place the recommendation
   panel alongside or directly adjacent to the catalogue/rating controls within
   the authenticated app screen. When a fresh prediction arrives, update that
   panel in place with movie titles and predicted scores. Show a clear updating
   indicator while computation is pending, and preserve the prior result until
   its replacement arrives. For a cold-start account, explain that five distinct
   ratings are needed; after the threshold, present the newly populated list in
   this same panel without navigation or a separate results page.
5. **Make rated items legible.** Show the user's rated titles and their current
   ratings in a compact, readable list, so duplicate edits/upserts are
   understandable and rated films can be distinguished during browsing.
6. **Work on narrow screens and with assistive technology.** Keep controls
   usable on mobile widths, provide keyboard-operable catalogue navigation and
   rating controls, label status updates for screen readers, and show empty,
   loading, and catalogue-error states.

## Implementation tasks

### U01 — Load and serve the movie title catalogue

- [x] Inspect `u.item` field encoding and title edge cases (pipes, quotes,
  backslashes, non-ASCII text, empty titles); define the exact ID/title mapping.
- [x] Add a catalogue reader/representation using the app's established Briev
  boundaries. Keep the MovieLens parsing and validation in Briev; do not add a
  Rust type/name or vocabulary special case.
- [x] Make `/movies` return stable records containing `item_id` and `title`,
  with internal IDs 0..1681. Ensure JSON escaping is correct and missing or
  malformed entries fail with an actionable startup/API error rather than
  silently shifting IDs.
- [x] Decide whether catalogue data is loaded once from the same configured
  dataset directory as `u.data` or packaged/copied beside the app; document the
  chosen path and deployment requirement.
- [x] Add focused fixtures for ID alignment, representative title characters,
  missing rows, and malformed input.

**2026-10-25 U01 implementation record:** `movie_catalogue.bv` loads a local
`u.item` file once during server startup (`UITEM_PATH`, default `u.item`),
validates all expected sequential IDs and nonempty titles, and converts each
ISO-8859-1 title byte to a Unicode character before JSON encoding. The catalogue
is retained in `ServerState`; `/movies` returns zero-based `item_id` and title
records and reports unavailable/invalid data as HTTP 503. No dataset bytes are
copied into the repository. `movie_catalogue_gate.bv` passed against the real
1682-row file, including the accented title byte and complete JSON serialization;
the API fixture and complete server compiled successfully. The PostgreSQL-backed
`server_api_gate` execution was not run because `PGUSER`/`PGDATABASE` are not
configured in this WSL shell; its catalogue response helper is exercised by the
database-independent catalogue fixture. Architecture and fixture-runner docs
record the path and wire contract.

### U02 — Build a browsable, live-search movie picker

- [ ] Replace the numeric movie input and numeric catalogue dump in
  `app.rbv` with a title-based catalogue view.
- [ ] Display a default page of titles before any search. Add bounded page size,
  previous/next controls, current page, total matches, and empty-result state.
- [ ] Filter available titles by the current query as it is typed, case
  insensitively. Reset pagination when the query changes; keep the query and
  selected film stable when the user changes pages where appropriate.
- [ ] Selecting a result identifies its internal item ID for submission while
  displaying the title to the user. Mark already-rated catalogue entries and
  show their current rating.
- [ ] Add deterministic behavior for empty queries and duplicate titles; title
  plus year may be displayed where it helps distinguish entries, without
  changing the engine's item identity.
- [ ] Add behavioral coverage for browsing, query matching, pagination
  boundaries, selection, and already-rated items.

### U03 — Make rating and live recommendations one experience

- [ ] Replace the numeric rating field with keyboard-accessible 1–5 star
  choices, retaining an explicit textual label/value for accessibility.
- [ ] Present pending/saved/failed state separately from prediction progress.
- [ ] Keep the recommendation panel in the authenticated primary screen next
  to the rating flow; remove wording/layout that makes it feel like a separate
  destination or view.
- [ ] Resolve recommendation item IDs to catalogue titles and show predicted
  scores in a readable ranked list. Render every new accepted-revision result
  in place as soon as it arrives; retain current stale-result rejection and
  ensure save confirmations never change the recommendation list.
- [ ] Clearly show the cold-start threshold and transition into live results
  when sufficient distinct ratings have been accepted.
- [ ] Add focused behavioral checks that title resolution works, result updates
  happen in place, and persistence events do not trigger a recommendation
  refresh or DOM replacement.

### U04 — Responsive and accessible visual pass

- [ ] Arrange browse/search/rating and recommendations as a balanced desktop
  layout that collapses cleanly on narrow screens; keep recommendations visible
  without requiring navigation away from rating.
- [ ] Add clear visual hierarchy for catalogue search, current selection,
  pending feedback, save status, calculation progress, and recommendation cards.
- [ ] Verify focus order, visible focus, semantic labels, live status messages,
  contrast, and touch target sizes.
- [ ] Capture desktop and narrow-screen browser evidence for initial, searching,
  selected/rated, calculating, cold-start, and populated recommendation states.

### U05 — Integration and handoff

- [ ] Run focused catalogue/parser, API, browser, and real server/live-channel
  checks. Preserve existing account, rating, reconnect, pending-save, and
  recommendation correctness behavior.
- [ ] Confirm `/movies` title IDs align with `u.data`/database item IDs for the
  complete 1682-item catalogue, not only sample entries.
- [ ] Update the relevant recommender frontend/API architecture or requirements
  documentation in the same logical change, preserving the existing
  rationale/history.
- [ ] Record changed paths, commands and outcomes, UI evidence, catalogue source
  assumptions, and any remaining issue here before marking the plan complete.
- [ ] If implementation exposes a Briev compiler or language defect, create a
  minimal reproducer, fix it in the compiler/language with regression coverage,
  and resume the app work against the corrected behavior. Do not add an app-side
  workaround for a compiler defect; keep compiler fixes and app changes in their
  proper independently reviewable change boundaries.

## Acceptance criteria

- Users can discover available titles by browsing without entering a query.
- Search results update from the currently typed text and include only matching
  catalogue titles; pagination remains correct at first, middle, and last pages.
- Every displayed title maps to the correct MovieLens item ID, and the complete
  catalogue has no silent ID shifts or omissions.
- Users can select and rate a title without seeing or entering a numeric ID.
- The recommendation panel remains in the same primary rating experience and
  updates in place when the latest valid prediction arrives, showing movie
  titles rather than `Movie N` labels.
- The UI communicates computation progress promptly and distinguishes it from
  database persistence status. A save completion alone does not recalculate or
  replace recommendations.
- Cold-start guidance, empty search, catalogue loading/error, pending save,
  save failure/retry, and narrow-screen layouts are understandable and usable.
- Existing account isolation, revision ordering, stale-result rejection, and
  recommendation algorithm semantics remain intact.

## Scope boundaries

- This plan changes the app's presentation and the catalogue data path needed
  for title display. It does not redo the independent backend responsiveness
  architecture tracked by `tasks-improvement.md`.
- No recommendation-algorithm changes, MovieLens ratings changes, or new
  backend language/runtime are in scope.
- Compiler and language development remains in scope when required for the app
  to express the intended behavior correctly. A compiler/language issue found
  during this work is fixed at its source, with a minimal reproducer and
  regression coverage; the app must not conceal it with a workaround. Keep that
  fix separate from the application change where repository workflow requires
  separate compiler and app change boundaries.
- Search and pagination operate over the finite MovieLens-100k catalogue. They
  must not imply that the app can rate films outside that dataset.
- The MovieLens dataset's included README states non-commercial/research usage
  terms and disallows redistribution without separate permission. Keep the
  catalogue source local/configured; do not copy or commit `u.item` into the
  repository without resolving the dataset's redistribution terms.

## Execution notes

Implementation has not started. Confirm the data path and deployment model in
U01 before coding, then complete U01 through U05 in order. Keep this plan as the
work ledger; record completion only after integration gates pass.
