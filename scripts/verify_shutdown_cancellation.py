#!/usr/bin/env python
"""Verify desktop shutdown persists cancellation for queued and running jobs."""

import os
import tempfile

with tempfile.TemporaryDirectory(prefix="bearreader-shutdown-jobs-") as data_dir:
    os.environ["XIAOXIONG_NOVEL_DATA_PATH"] = data_dir

    import sqlmodel as sq

    from lncrawl.context import ctx
    from lncrawl.dao import Job, JobStatus, JobType

    ctx.setup(log_level=0, reset_db_on_failure=True)
    try:
        user = ctx.users.get_admin()
        pending = ctx.jobs._create(user, JobType.SEARCH_ALL_SOURCES, {"query": "pending"})
        running = ctx.jobs._create(user, JobType.SEARCH_ALL_SOURCES, {"query": "running"})
        with ctx.db.session() as sess:
            sess.exec(sq.update(Job).where(Job.id == running.id).values(status=JobStatus.RUNNING))
            sess.commit()

        assert ctx.jobs.cancel_active_for_shutdown() == 2
        assert ctx.jobs.get(pending.id).status == JobStatus.CANCELED
        assert ctx.jobs.get(running.id).status == JobStatus.CANCELED
        assert ctx.jobs.get(pending.id).is_done
        assert ctx.jobs.get(running.id).is_done
        print("DESKTOP SHUTDOWN JOB CANCELLATION: PASS")
    finally:
        ctx.destroy()
