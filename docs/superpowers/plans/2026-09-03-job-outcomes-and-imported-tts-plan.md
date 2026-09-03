# Job Outcomes and Imported TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make aggregate job outcomes truthful and search empty states clear, while preventing imported EPUB/TXT speech requests from exceeding the backend limit.

**Architecture:** Add a numeric partial job status and derive aggregate completion from failures without changing the database schema. Record search-source outcomes in job metadata for stable UI statistics. Build imported-only speech segments in a pure frontend helper, leaving scraped-book segmentation unchanged.

**Tech Stack:** Python, SQLModel/SQLAlchemy, React 19, TypeScript, Ant Design 6, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-03-job-outcomes-and-imported-tts-design.md`

## Global Constraints

- Do not change EPUB/TXT import confirmation or Chinese export filenames.
- Do not add search action buttons.
- Do not change scraped-novel TTS segmentation.
- Keep the backend 2,000-character TTS validation limit.
- Do not edit `lncrawl/server/web/` by hand; synchronize it from the frontend build.
- Do not push. Any requested commit uses `Bearladin <bearladin@users.noreply.github.com>` as both author and committer.

---

### Task 1: Aggregate job status

**Files:**
- Modify: `lncrawl/enums.py`
- Modify: `lncrawl/services/jobs/service.py`
- Modify: `lncrawl/services/scheduler/handlers/_base.py`

**Interfaces:**
- Produces: `JobStatus.PARTIAL = 6` and completion aggregation shared by all batch handlers.

- [ ] Add the `PARTIAL` enum value and make completed ancestors with failures partial instead of successful.
- [ ] Make a batch whose direct children all failed finish as failed.
- [ ] Exercise success, partial and all-failed cases against a temporary SQLite database.

### Task 2: Search outcome metadata

**Files:**
- Modify: `lncrawl/services/scheduler/handlers/search_all_sources.py`
- Modify: `lncrawl/services/scheduler/handlers/search_source.py`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Produces: `search_source_total`, `search_sources`, `search_completed`, and `search_result_count` fields in `Job.extra`.

- [ ] Record the number of participating searchable sources when the parent expands.
- [ ] Record one idempotent completed/failed outcome per source, including zero-result success.
- [ ] Preserve existing result aggregation and metadata fetching behavior.

### Task 3: Search and partial-status presentation

**Files:**
- Create: `frontend/src/pages/JobDetails/searchOutcome.ts`
- Create: `frontend/src/pages/JobDetails/searchOutcome.test.ts`
- Modify: `frontend/src/pages/JobDetails/SearchResultsCard.tsx`
- Modify: `frontend/src/pages/JobDetails/index.tsx`
- Modify: `frontend/src/components/Tags/JobStatusTag.tsx`
- Modify: `frontend/src/components/Tags/JobFailCountTag.tsx`
- Modify: `frontend/src/pages/JobList/JobProgessBar.tsx`
- Modify: `frontend/src/pages/JobList/constants.ts`
- Modify: `frontend/src/locales/zh-CN.ts`
- Modify: `frontend/src/types/enums.ts`

**Interfaces:**
- Produces: `getSearchOutcome(job)` with presentation kind, result count, source totals and source failures.

- [ ] Write table-driven tests for running, found, found-partial, no-results, incomplete-no-results and all-failed searches.
- [ ] Implement the pure outcome helper and run its tests.
- [ ] Restrict the search card to search jobs and replace the faint empty state with compact semantic alerts.
- [ ] Add partial status labels, filter, tag and restrained warning-colored progress.
- [ ] Show source-specific failure counts for all-source search jobs.

### Task 4: Imported EPUB/TXT TTS segmentation

**Files:**
- Create: `frontend/src/pages/NovelReader/ttsSegments.ts`
- Create: `frontend/src/pages/NovelReader/ttsSegments.test.ts`
- Modify: `frontend/src/pages/NovelReader/ReaderVerticalContent.tsx`

**Interfaces:**
- Produces: `buildTtsSegments(contentEl, { imported, chapterTitle })` returning ordered `{ text, element }` entries and `splitTtsText(text, maxLength)`.

- [ ] Write tests proving punctuation splits are at most 1,500 characters and preserve all text.
- [ ] Implement imported leaf-block extraction, duplicate-heading speech suppression and safe splitting.
- [ ] Drive playback, prefetch, focus and click position from speech segments.
- [ ] Verify the non-imported path keeps one segment per original top-level child.

### Task 5: Documentation, synchronization and release verification

**Files:**
- Modify: `CHANGELOG.md`
- Generate from frontend: `lncrawl/server/web/`

**Interfaces:**
- Consumes: all completed implementation tasks.
- Produces: tested source, synchronized web bundle, portable ZIP, patch and handoff document.

- [ ] Add concise CHANGELOG entries for truthful partial/search outcomes and imported-book TTS chunking.
- [ ] Run frontend tests, lint and build.
- [ ] Synchronize the generated frontend using the repository script and verify it.
- [ ] Run repository lint and targeted runtime checks.
- [ ] Review the diff for scope, secrets and generated-file consistency.
- [ ] Commit with the explicitly requested Bearladin identity without pushing.
- [ ] Build and inspect the portable ZIP, generate PATCH3, and update the consolidated handoff document in the local PATCH3 handoff directory.
