# Reader Review Fixes Design

**Date:** 2026-08-31  
**Status:** Approved for implementation planning

## Goal

Resolve all confirmed defects from the 2026-08-31 code review in one focused batch:

- prevent saved scroll updates from resetting TTS to the first paragraph;
- release TTS audio resources when a chapter component unmounts;
- support font-size shortcuts on both the main keyboard and numeric keypad;
- prevent Space from changing a toolbar action after a mouse click;
- correct library search counts and cached library totals;
- prevent stale list requests from overwriting current results;
- remove the local-source reload action from the release UI.

This batch will not add a user-facing custom-source system, produce a new ZIP package, or push any commit.

## Design Principles

Use small root-cause fixes at existing boundaries rather than isolated special cases or a reader-control rewrite. Preserve current Redux state, API contracts, TTS cross-chapter behavior, and the backend local-source reload mechanism.

## Reader Keyboard and Focus Behavior

The reader's global key handler will continue to ignore Ctrl, Alt, and Meta combinations, editable elements, and interactive controls.

Unmodified `+` and `-` will adjust the reader font by 1 px. Detection will cover:

- main keyboard `+` and `-` through `KeyboardEvent.key`;
- numeric keypad add and subtract through `KeyboardEvent.code` values `NumpadAdd` and `NumpadSubtract`.

Key repeat is allowed. The existing Redux reducer remains the single enforcement point for the 12–32 px range.

Mouse activation of a reader toolbar control will release its focus, so a subsequent Space press reaches the reader and scrolls one screen. Keyboard users may still Tab to a toolbar control and activate it with Enter or Space. A keyboard activation handled by a control must not propagate to the global reader shortcut handler.

The focus rule applies consistently to reader toolbar actions, not only the two font-size controls.

## Scroll Restoration and TTS Position

Chapter initialization and ongoing scroll persistence will be separate lifecycles.

When the chapter identity changes, the reader will:

1. read the saved position for that novel once;
2. restore it only if it belongs to the opened chapter, otherwise scroll to the top;
3. reset the TTS paragraph position to zero;
4. stop TTS only when the completed chapter has no readable content.

Subsequent `lastReads` updates from manual scrolling, automatic scrolling, or TTS-follow scrolling must not rerun chapter initialization.

If TTS is already active during chapter navigation, it remains active and starts the new chapter from its first paragraph.

## TTS Resource Lifecycle

The TTS hook will own an explicit unmount cleanup independent of the global `speaking` state. Cleanup will:

- prevent late asynchronous work from updating an obsolete chapter instance;
- cancel supported in-flight audio requests;
- pause and detach the current audio player;
- revoke every cached Blob URL;
- clear cached and in-flight request bookkeeping.

Stopping TTS within a mounted chapter will retain equivalent cleanup behavior. Expected cancellation will not show an error; genuine synthesis or playback failures will continue to surface through the existing error message.

## Library Counts

The library list and filtered count queries will use the same `Novel`-to-`LibraryNovel` join and the same search predicate. This removes the Cartesian product and makes pagination totals match returned items.

`library.extra.novel_count` represents the full library size. A filtered search total must never overwrite it. The cache may be refreshed only from an unfiltered count.

No schema or API response change is required.

## Stale Request Prevention

The full novel list and library novel list will cancel their previous request whenever query inputs change or the component unmounts. Axios requests will receive an `AbortController` signal.

Only explicit cancellation is ignored. Other request failures continue to populate the existing error state. Loading state may be finalized only by the active request, so a canceled older request cannot hide a newer request's loading indicator.

## Local Source Reload UI

The “重新加载本地书源” button, handler, and now-unused imports will be removed from the supported-sources page.

The backend endpoint and `ctx.sources.reload_local()` will remain intact for development, runtime verification, and a possible future custom-source feature. The incorrect displayed reload time and cache behavior become unreachable in the release UI and therefore are not separately redesigned in this batch.

A future custom-source feature requires a separate design because local source files are arbitrary Python code executed with application permissions. It must address installation, trust, validation, sandboxing or explicit risk acceptance, editing, and anti-bot limitations before restoring the button.

## Files and Generated Output

Expected source areas:

- `frontend/src/pages/NovelReader/`
- `frontend/src/pages/NovelList/hooks.ts`
- `frontend/src/pages/LibraryDetails/LibraryNovelList.tsx`
- `frontend/src/pages/SupportedSources/index.tsx`
- `lncrawl/services/libraries.py`
- `CHANGELOG.md`

After frontend source changes pass validation, regenerate the committed embedded frontend through the repository's existing synchronization scripts and verify `frontend-manifest.json`. Generated web assets must not be edited manually.

## Validation

Run existing gates only:

- backend: `make lint`;
- frontend: `yarn lint`, `yarn build`, and `yarn audit:zh`;
- embedded frontend synchronization and manifest verification.

Manual acceptance matrix:

1. Main keyboard and numeric keypad `+`/`-` change font size by 1 px and clamp at 12–32 px.
2. Clicking any reader toolbar action and then pressing Space only scrolls.
3. Tabbing to a toolbar action allows Enter/Space activation without scrolling.
4. Manual, automatic, and TTS-follow scrolling no longer reset the active TTS paragraph.
5. Reopening a chapter restores its saved offset; switching chapters initializes the new chapter once.
6. TTS reads multiple paragraphs and crosses chapters without retaining old chapter audio resources.
7. Library search total equals its actual matching items and does not replace the library's full count.
8. Rapid changes to search or sorting cannot display an older response on either list page.
9. The supported-sources page has no local-source reload action.

## Delivery Constraints

- Do not build or publish a new ZIP package.
- Complete implementation and validation before creating a Git commit.
- A local commit is authorized only for this approved batch after all work is complete.
- Do not push under any circumstances.
- After the commit, write a Chinese handoff report to the Desktop `markdown` directory.
- Export the completed commit as a binary-safe Git format-patch into the same directory,
  record its SHA-256 checksum, and verify that it can reproduce the committed tree from
  the commit's parent.
