from threading import Event
from typing import List, Type

from ....dao import Job
from ._base import BaseHandler, FallbackHandler
from .artifact import ArtifactHandler
from .artifact_batch import ArtifactBatchHandler
from .chapter import ChapterHandler
from .chapter_batch import ChapterBatchHandler
from .chapter_translation import ChapterTranslationHandler
from .chapter_translation_batch import ChapterTranslationBatchHandler
from .fetch_latest import FetchLatestHandler
from .fetch_missing import FetchMissingHandler
from .image import ImageHandler
from .image_batch import ImageBatchHandler
from .import_epub import EpubAnalyzeHandler, EpubCommitHandler
from .novel import NovelHandler
from .novel_batch import NovelBatchHandler
from .novel_translation import NovelTranslationHandler
from .novel_translation_batch import NovelTranslationBatchHandler
from .search_all_sources import SearchAllSourcesHandler
from .search_source import SearchSourceHandler
from .volume import VolumeHandler
from .volume_batch import VolumeBatchHandler
from .volume_translation import VolumeTranslationHandler
from .volume_translation_batch import VolumeTranslationBatchHandler

# To add a new handler: create the module, import its class here, and add it below.
_HANDLER_REGISTRY: List[Type[BaseHandler]] = [
    NovelHandler,
    NovelBatchHandler,
    NovelTranslationHandler,
    NovelTranslationBatchHandler,
    FetchMissingHandler,
    FetchLatestHandler,
    VolumeHandler,
    VolumeBatchHandler,
    VolumeTranslationHandler,
    VolumeTranslationBatchHandler,
    ChapterHandler,
    ChapterBatchHandler,
    ChapterTranslationHandler,
    ChapterTranslationBatchHandler,
    ImageHandler,
    ImageBatchHandler,
    EpubAnalyzeHandler,
    EpubCommitHandler,
    ArtifactHandler,
    ArtifactBatchHandler,
    SearchAllSourcesHandler,
    SearchSourceHandler,
    FallbackHandler,
]


def run_job(job: Job, signal: Event) -> bool:
    for handler in _HANDLER_REGISTRY:
        if handler.can_activate(job):
            return handler(job, signal).process()
    return False
