"""Exception hierarchy and refresh diagnostic redaction.

CLI exit codes: 0 success, 1 any AiProfileError, 2 usage.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum

_PATH_FREE_DIAGNOSTICS: ContextVar[bool] = ContextVar(
    "aiprofile_path_free_diagnostics", default=False
)


@contextmanager
def path_free_diagnostics(enabled: bool = True):
    """Select path-free operational diagnostics for one call context.

    Refresh uses this at default verbosity so warnings emitted by lower
    layers cannot disclose local paths.  ``-v`` leaves the original local
    detail intact and the CLI prints the chained traceback.
    """
    token = _PATH_FREE_DIAGNOSTICS.set(enabled)
    try:
        yield
    finally:
        _PATH_FREE_DIAGNOSTICS.reset(token)


def diagnostic_text(public: str, local: str) -> str:
    """Return the privacy-safe or local-detail form for this context."""
    return public if _PATH_FREE_DIAGNOSTICS.get() else local


class AiProfileError(Exception):
    """Base for all operational errors surfaced to the CLI."""


class ConfigError(AiProfileError):
    """Configuration missing, malformed, or inconsistent."""


class GitError(AiProfileError):
    """A git invocation failed or the path is not a usable repository.

    Messages may include the failing command and stderr excerpt; they are
    terminal-only and must never be written into generated assets
    (architecture.md section 10 diagnostics rule).
    """


class StorageError(AiProfileError):
    """SQLite storage or migration failure."""


class LockError(AiProfileError):
    """The per-home refresh lock is contended or unavailable.

    Messages distinguish actual contention from unsupported/inaccessible
    locking while following the default-output privacy rule: no filesystem
    path, repository name, or basename.
    """


class RefreshFailureState(Enum):
    """What callers can safely conclude after an exceptional refresh."""

    NOT_PUBLISHED = "not_published"
    PARTIAL_OUTPUT = "partial_output"
    PUBLISHED_FINALIZATION_FAILED = "published_finalization_failed"


_REFRESH_FAILURE_MESSAGES = {
    RefreshFailureState.NOT_PUBLISHED: (
        "refresh failed safely; no new asset generation was published"
    ),
    RefreshFailureState.PARTIAL_OUTPUT: (
        "refresh failed during publication; partial generated assets or recovery"
        " backups may remain; inspect the output directory locally before publishing"
    ),
    RefreshFailureState.PUBLISHED_FINALIZATION_FAILED: (
        "the new asset generation was published, but refresh finalization or lock"
        " release failed; verify local state before retrying"
    ),
}


class RefreshError(AiProfileError):
    """Exceptional refresh outcome with a structured publication state.

    The message is safe for default output.  The original exception is
    retained through exception chaining for the explicit ``-v`` channel.
    """

    def __init__(self, state: RefreshFailureState) -> None:
        self.state = state
        super().__init__(_REFRESH_FAILURE_MESSAGES[state])


class SchemaValidationError(AiProfileError):
    """An ACE event violated docs/schema.md; never coerced, always rejected."""


class RenderError(AiProfileError):
    """Rendering or export failure."""


class IncompleteRollbackError(RenderError):
    """Asset publication failed and rollback could not fully recover.

    Asset names and the output path remain local detail in the exception
    message.  Refresh maps the TYPE and structured fields to a path-free
    public outcome; ``-v`` exposes this original chained exception.
    """

    def __init__(
        self,
        message: str,
        *,
        unrestored: tuple[str, ...],
        unretracted: tuple[str, ...],
    ) -> None:
        self.unrestored = unrestored
        self.unretracted = unretracted
        super().__init__(message)
