from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class LoggingConfig:
    package_name: str
    level: int = logging.INFO

    # Handlers
    console: bool = True
    logdir: Optional[Path] = None
    logfile_prefix: str = "run"

    # Multiprocessing / uniqueness
    include_pid_in_filename: bool = True

    # Hygiene / UX
    clear_handlers: bool = True          # important for re-entry and forked children
    propagate: bool = False              # avoid double logging via root
    include_third_party: bool = False    # optionally quiet noisy libs below

def configure_logging(
    *,
    package_name: str,
    level: int = logging.INFO,
    console: bool = True,
    logdir: Optional[Path] = None,
    logfile_prefix: str = "run",
    include_pid_in_filename: bool = True,
    clear_handlers: bool = True,
    propagate: bool = False,
    include_third_party: bool = False,
) -> Path | None:
    return configure_logging_config(
        LoggingConfig(
            package_name=package_name,
            level=level,
            console=console,
            logdir=logdir,
            logfile_prefix=logfile_prefix,
            include_pid_in_filename=include_pid_in_filename,
            clear_handlers=clear_handlers,
            propagate=propagate,
            include_third_party=include_third_party,
        )
    )


def configure_logging_config(cfg: LoggingConfig) -> Path | None:
    """
    Configure logging for a package + (optionally) a logfile.

    Contract:
    - Only configures the *package* logger tree rooted at cfg.package_name.
    - Safe to call multiple times (when cfg.clear_handlers=True).
    - Returns logfile path if a file handler is created; otherwise returns None.
    """
    pkg_logger = logging.getLogger(cfg.package_name)
    pkg_logger.setLevel(cfg.level)
    pkg_logger.propagate = cfg.propagate

    if cfg.clear_handlers:
        # Crucial for:
        # - repeated calls during development/tests
        # - forked multiprocessing children inheriting handlers
        pkg_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(process)d] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Console handler ---
    if cfg.console:
        sh = logging.StreamHandler(stream=sys.stderr)
        sh.setLevel(cfg.level)
        sh.setFormatter(formatter)
        pkg_logger.addHandler(sh)

    # --- File handler ---
    logfile_path: Path | None = None
    if cfg.logdir is not None:
        cfg.logdir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = os.getpid() if cfg.include_pid_in_filename else None

        name_bits = [cfg.logfile_prefix, ts]
        if pid is not None:
            name_bits.append(f"pid{pid}")
        filename = "_".join(name_bits) + ".log"

        logfile_path = cfg.logdir / filename

        fh = logging.FileHandler(logfile_path, encoding="utf-8")
        fh.setLevel(cfg.level)
        fh.setFormatter(formatter)
        pkg_logger.addHandler(fh)

    # --- Optional: tame noisy third-party loggers ---
    if not cfg.include_third_party:
        # Typical offenders; adjust to taste
        for noisy in ("urllib3", "botocore", "matplotlib", "fiona", "rasterio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    # Helpful: also expose the chosen file path as a debug message
    if logfile_path is not None:
        pkg_logger.debug("Logging to file: %s", logfile_path)

    return logfile_path



def resolve_loglevel(
    *,
    debug: bool = False,
    quiet: bool = False,
    verbose: int = 0,
    loglevel: Optional[str] = None,
) -> tuple[int, bool]:
    """
    Convert common CLI flags into a logging level + console enable flag.

    - quiet controls console only (file logging remains available via logdir)
    - explicit loglevel overrides debug/verbose
    """
    console = not quiet

    if loglevel is not None:
        # Accept strings like "INFO", "debug", etc.
        name = str(loglevel).upper()
        if not hasattr(logging, name):
            raise ValueError(f"Invalid loglevel={loglevel!r}")
        level = getattr(logging, name)
        return level, console

    if debug or verbose >= 2:
        return logging.DEBUG, console

    # If you want -v to mean INFO and default to INFO anyway, this is redundant
    # but harmless and explicit.
    if verbose >= 1:
        return logging.INFO, console

    return logging.INFO, console