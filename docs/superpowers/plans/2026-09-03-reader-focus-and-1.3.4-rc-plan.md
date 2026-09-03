# Reader Focus and 1.3.4 RC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore visible and scroll-following TTS focus for imported and scraped novels, then build a locally testable BearReader 1.3.4 release candidate.

**Architecture:** Resolve scraped-book focus from the live top-level DOM and imported-book focus from validated nested speech segments. Keep the version in `lncrawl/VERSION`, add a new 1.3.4 release-notes section without rewriting 1.3.2 history, and rebuild the embedded frontend and Windows portable bundle.

**Tech Stack:** React 19, TypeScript, SCSS modules, Vitest, Python, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-09-03-reader-focus-and-1.3.4-rc-design.md`

## Global Constraints

- Keep imported EPUB/TXT speech chunking and the backend 2,000-character limit.
- Preserve scraped-book text segmentation and the reading-position persistence format.
- Preserve the published 1.3.2 changelog section; add 1.3.4 above it.
- Do not edit `lncrawl/server/web/` manually.
- Do not push, tag, trigger CI, or publish a release.
- Commit author and committer must be `Bearladin <bearladin@users.noreply.github.com>`.

---

### Task 1: Reader focus regression

**Files:**
- Modify: `frontend/src/pages/NovelReader/ttsSegments.ts`
- Modify: `frontend/src/pages/NovelReader/ttsSegments.test.ts`
- Modify: `frontend/src/pages/NovelReader/ReaderVerticalContent.tsx`
- Modify: `frontend/src/pages/NovelReader/ReaderVerticalLayout.module.scss`

**Interfaces:**
- Produces: `selectLiveTtsSegments(cached, imported, rebuildImported)` plus `resolveTtsFocusElement(contentEl, segments, position, imported)`, so imported DOM operations rebuild current elements while audio retains cached text.

- [ ] Write failing tests for live top-level scraped focus, nested imported focus and disconnected imported nodes.
- [ ] Implement live imported-segment selection and route highlighting through a connected current-DOM resolver.
- [ ] Restore the original top-level click calculation for scraped books while retaining nested imported click mapping.
- [ ] Change the focus selector from direct-child to descendant scope.
- [ ] Run the focused tests, full frontend tests, lint and build.

### Task 2: Version and release notes

**Files:**
- Modify: `lncrawl/VERSION`
- Modify: `CHANGELOG.md`
- Modify: `frontend/src/pages/Changelog/index.tsx`

**Interfaces:**
- Produces: application version 1.3.4 and matching backend/frontend release notes.

- [ ] Set `lncrawl/VERSION` to `1.3.4` without changing any other version source.
- [ ] Restore the origin 1.3.2 changelog section and add a concise 1.3.4 section covering PATCH1–PATCH4.
- [ ] Add the matching user-facing 1.3.4 group to the in-app changelog.
- [ ] Verify the frontend title and CLI version both report 1.3.4.

### Task 3: Distribution and delivery

**Files:**
- Generate: `lncrawl/server/web/`
- Modify: `frontend-manifest.json`
- Modify: the consolidated 0903 handoff document (BearReader-完整交接-2026-09-03-PATCH1-PATCH2-PATCH3-PATCH4.md)

**Interfaces:**
- Produces: one PATCH4, one cumulative 1.3.4 portable ZIP and one cumulative handoff document.

- [ ] Synchronize and verify the embedded frontend.
- [ ] Run Pyright, Ruff, frontend tests, ESLint and production build.
- [ ] Build and verify the Windows bundle and source inventory.
- [ ] Commit locally with the required identity and confirm the worktree is clean.
- [ ] Generate PATCH4 and verify it applies after PATCH3 with an identical final tree.
- [ ] Build the 1.3.4 portable ZIP, test archive integrity and inspect embedded version/fix markers.
- [ ] Move the cumulative handoff document from PATCH3 to PATCH4 and update status, hashes, verification, pitfalls and PATCH order.
