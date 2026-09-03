# Reader Review Fixes Implementation Plan

**Design:** `docs/superpowers/specs/2026-08-31-reader-review-fixes-design.md`  
**Delivery:** one local commit after all work and validation; no ZIP; never push

## 1. Preflight

**Files:** none

1. Confirm `git status --short --branch` contains only the approved design and plan documents.
2. Confirm HEAD remains `73cd8db` and the local `pre-push` hook rejects pushes.
3. Record the existing generated frontend state; do not edit `lncrawl/server/web/` manually.

## 2. Correct Library Search Counts

**File:** `lncrawl/services/libraries.py`

1. Build the count query from `Novel` joined to `LibraryNovel`, matching the list query's relationship.
2. Apply the same library ID and optional title/author predicates to both list and filtered count queries.
3. Preserve all existing sort branches, offset, limit, and response DTO behavior.
4. Update `library.extra.novel_count` only when `search.strip()` is empty, because a filtered result is not the library's total size.
5. Inspect the resulting SQL path for both empty and non-empty search values and confirm no implicit second `Novel` FROM remains.

## 3. Separate Chapter Initialization From Scroll Persistence

**File:** `frontend/src/pages/NovelReader/index.tsx`

1. Stop subscribing the restoration effect to the changing `lastReads` object.
2. Split chapter behavior into:
   - a chapter-identity effect that resets `speakPosition` once and applies the existing no-content stop condition;
   - a guarded restoration effect that waits for readable chapter content, reads the latest saved record directly from the store once, then performs the existing double-`requestAnimationFrame` scroll.
3. Track the restored chapter ID in a ref so a chapter that initially waits for download restores after content appears, but later scroll writes do not restore again.
4. Reset the guard when navigating to a different chapter.
5. Keep the existing 500 ms scroll-write throttle and offset clamp.
6. Manually reason through these paths before moving on:
   - opening a previously read completed chapter;
   - opening an undownloaded chapter and receiving content later;
   - TTS-follow scrolling within one chapter;
   - TTS crossing to the next chapter.

## 4. Make TTS Cleanup Own Its Component Lifecycle

**File:** `frontend/src/pages/NovelReader/ReaderVerticalContent.tsx`

1. Introduce one request-cancellation controller owned by the mounted TTS hook instance.
2. Pass its signal to `/api/tts/synthesize` requests.
3. Centralize resource cleanup so stop and unmount both:
   - mark the current session stopped;
   - abort in-flight synthesis requests;
   - pause and detach the current `Audio`;
   - revoke every cached Blob URL;
   - clear audio and in-flight maps.
4. Renew the controller when the same mounted chapter starts a later speaking session; never reuse an aborted signal.
5. Add an unmount-only effect that performs final cleanup even when global `speaking` remains true during chapter navigation.
6. In the main playback error path, ignore only an abort caused by stop/unmount. Preserve the existing user-facing error for genuine synthesis failures.
7. Ensure late completions cannot publish or play audio for an obsolete chapter.
8. Preserve prefetch count, cache cap, MediaSession handlers, paragraph progression, and next-chapter navigation.

## 5. Unify Reader Keyboard and Toolbar Focus Rules

**Files:**

- `frontend/src/pages/NovelReader/index.tsx`
- `frontend/src/pages/NovelReader/ReaderNavBar.tsx`
- `frontend/src/pages/NovelReader/ReaderSettingsButton.tsx`
- `frontend/scripts/audit-localization.mjs` only if the localization audit requires new technical key names

1. Add a focused helper in the reader module for deciding whether a key event originated from an editable or interactive control.
2. Make the global reader handler return for interactive controls in addition to input, textarea, and contenteditable targets.
3. Add font-size branches before the Space branch:
   - `event.key === '+'` or `event.code === 'NumpadAdd'` increases by 1 px;
   - `event.key === '-'` or `event.code === 'NumpadSubtract'` decreases by 1 px.
4. Read the current font size from the Redux store at event time, dispatch through the existing clamped reducer, call `preventDefault()`, and allow key repeat.
5. Preserve the existing Ctrl/Alt/Meta exclusion so browser or system combinations are untouched.
6. Update the shared toolbar keyboard handler to stop propagation after handling Enter or Space.
7. Prevent mouse/pointer activation from leaving each simulated toolbar button focused, while retaining Tab focus and Enter/Space activation for keyboard users.
8. Apply the same focus rule to the settings control and all reader toolbar actions, not just font controls.
9. Confirm a mouse click followed by Space reaches only the page-scroll shortcut, while a Tab-focused action consumes Space locally.

## 6. Prevent Stale Novel List Responses

**Files:**

- `frontend/src/pages/NovelList/hooks.ts`
- `frontend/src/pages/LibraryDetails/LibraryNovelList.tsx`

1. Create an `AbortController` for each query effect execution.
2. Pass its signal to Axios and abort it from effect cleanup.
3. In the full-list hook, preserve the 50 ms debounce timer and abort requests that have already started.
4. Set loading at the start of each active query.
5. Ignore only Axios cancellation or an aborted signal; continue converting all real failures with `stringifyError`.
6. In `finally`, update loading only when that request's signal was not aborted, preventing an older cleanup from hiding a newer load.
7. Preserve URL parameters, pagination reset behavior, manual refresh, search trimming, and all current result rendering.

## 7. Remove the Release UI for Local Source Reload

**File:** `frontend/src/pages/SupportedSources/index.tsx`

1. Remove the reload button and `handleUpdateSources`.
2. Remove imports and state used only by that action: admin selection, message context, Axios, date formatting, reload icon, and error stringification as applicable.
3. Keep supported-source fetching, filtering, tabs, counts, and retry behavior unchanged.
4. Do not change:
   - `POST /api/admin/update-sources`;
   - `AdminService.update_sources`;
   - `Sources.reload_local`;
   - local user-source scanning.

## 8. Document User-Visible Fixes

**File:** `CHANGELOG.md`

1. Add concise entries under `## [Unreleased]` for:
   - reliable reader keyboard/focus and font shortcuts;
   - stable TTS progression and cleanup;
   - correct library search totals and current list results;
   - removal of the misleading local-source reload action.
2. Keep one line per paragraph and do not edit generated README or source-index regions.

## 9. Run Source Validation Gates

**Files:** source changes above

1. From the repository root, run:

   ```powershell
   make lint
   ```

2. From `frontend\`, run:

   ```powershell
   yarn lint
   yarn build
   yarn audit:zh
   ```

3. Fix only failures caused by this batch. Do not introduce new lint or test tooling.

## 10. Synchronize and Verify Embedded Frontend

**Files generated by existing tools:**

- `lncrawl/server/web/`
- `frontend-manifest.json`

1. After the frontend gates pass, run from the repository root:

   ```powershell
   make frontend-sync
   make frontend-verify
   make web-verify
   ```

2. Review the generated diff and confirm it corresponds only to approved frontend source changes.
3. Do not run `make index-gen`.
4. Do not run any wheel, executable, installer, portable, or ZIP build.

## 11. Manual Acceptance Pass

Run the application through the existing development command and verify:

1. Main keyboard and numeric keypad `+`/`-` change font size by exactly 1 px and clamp at 12–32 px.
2. Mouse-clicking every reader toolbar action and then pressing Space only scrolls.
3. Tabbing to each toolbar action allows Enter/Space activation without scrolling.
4. Arrow and `S` shortcuts retain their documented behavior.
5. Saved scroll position restores once when reopening a chapter.
6. Manual scrolling and TTS-follow scrolling do not reset the speaking paragraph.
7. TTS reads multiple paragraphs, crosses a chapter boundary, and releases the old chapter's requests, player, cache, and Blob URLs.
8. Library search totals match visible results and the full library count remains correct after clearing search.
9. Rapid search and sort changes on both novel lists end with the newest query's results.
10. The supported-sources page no longer exposes the local reload action.

Stop the development process by its specific PID after validation.

## 12. Final Review and Local Commit

1. Run `git diff --check`.
2. Review `git diff --stat` and the complete source diff; confirm no unrelated files, ZIPs, installers, source-index regeneration, or secrets are present.
3. Re-run the smallest failed gate if any fix was made after the main validation pass.
4. Confirm Author and Committer both resolve to:

   ```text
   Bearladin <bearladin@users.noreply.github.com>
   ```

5. Create one local commit for the complete approved batch, including the design, plan, source changes, changelog, embedded frontend, and manifest.
6. Confirm the worktree is clean and the local branch is ahead of `origin/main`.
7. Do not run `git push`, tag commands, release commands, or ZIP packaging.

## 13. Export and Verify the Git Patch

**Output directory:** the maintainer's local handoff directory

1. Export the one completed commit with `git format-patch -1 --binary`. Use a filename that
   includes the feature and short commit SHA, for example:

   ```text
   BearReader-reader-review-fixes-<short-sha>.patch
   ```

2. Generate a SHA-256 checksum for the patch.
3. Create a temporary detached worktree from the completed commit's parent.
4. Apply the patch there with `git am --3way`.
5. Confirm the temporary worktree's resulting tree hash exactly equals the completed local
   commit's tree hash.
6. Remove the temporary worktree after verification.
7. Do not create a ZIP, tag, release, or push.

The patch must contain the complete single commit, including Author/Committer metadata,
design and plan documents, source changes, changelog, embedded frontend, and manifest.
Repository-local Git configuration and `.git\hooks\pre-push` are intentionally not part of
the patch because Git never includes `.git` state.

## 14. Write the Chinese Handoff Document

**Output:** `BearReader-阅读器审核修复交接-2026-08-31.md` in the maintainer's local handoff directory

Write the report after the commit and patch exist so all identifiers are final. Include:

1. goal and approved product decisions;
2. base commit and completed commit SHA;
3. Author and Committer identity;
4. files and meaningful behavior changed;
5. automated gates and manual checks completed, including any check that could not be run;
6. known limitations and deferred custom-source work;
7. exact patch filename, file size, and SHA-256;
8. home-computer prerequisites and application commands;
9. conflict recovery and rollback instructions;
10. explicit confirmation that no ZIP was built and no push occurred.

Recommended home-computer procedure:

```powershell
git status --short --branch
git fetch origin
git am --3way "C:\path\to\BearReader-reader-review-fixes-<short-sha>.patch"
git status --short --branch
git --no-pager log -1 --format="Author: %an <%ae>%nCommitter: %cn <%ce>%nSubject: %s"
```

The home worktree must be clean before `git am`. If conflicts occur, resolve them and run
`git am --continue`; to abandon the operation, run `git am --abort`. Do not use `git apply`
for the primary workflow because it does not preserve the commit metadata as directly as
`git am`.
