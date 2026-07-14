"""Exception hierarchy (architecture.md section 10).

CLI exit codes: 0 success, 1 any AiProfileError, 2 usage.
"""


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


class SchemaValidationError(AiProfileError):
    """An ACE event violated docs/schema.md; never coerced, always rejected."""


class RenderError(AiProfileError):
    """Rendering or export failure."""
