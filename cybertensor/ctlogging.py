# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2024 cyber~Congress

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import argparse
import copy
import os
import sys
import re
from typing import Optional

import torch
from loguru import logger

from cybertensor.config import Config


logger = logger.opt(colors=True)
# Remove default sink.
try:
    logger.remove(0)
except Exception:
    pass


def _remove_loguru_ansi_directive(text: str) -> str:
    pattern = r"<.*?>"
    return re.sub(pattern, "", text)


class logging:
    """Standardized logging for cybertensor."""

    __has_been_inited__: bool = False
    __debug_on__: bool = False
    __trace_on__: bool = False
    __std_sink__: int = None
    __file_sink__: int = None
    __off__: bool = False

    @classmethod
    def off(cls):
        """Turn off all logging output."""
        if not cls.__has_been_inited__:
            cls()
        cls.__off__ = True

        for handler_id in list(logger._core.handlers):
            logger.remove(handler_id)

    @classmethod
    def on(cls):
        """Turn on logging output by re-adding the sinks."""
        if cls.__off__:
            cls.__off__ = False

            cls.__std_sink__ = logger.add(
                sys.stdout,
                level=0,
                filter=cls.log_filter,
                colorize=True,
                enqueue=True,
                backtrace=True,
                diagnose=True,
                format=cls.log_formatter,
            )

            # Check if logging to file was originally enabled and re-add the file sink
            if cls.__file_sink__ is not None:
                config = cls.config()
                filepath = config.logging.logging_dir + "/logs.log"
                cls.__file_sink__ = logger.add(
                    filepath,
                    filter=cls.log_save_filter,
                    enqueue=True,
                    backtrace=True,
                    diagnose=True,
                    format=cls.log_save_formatter,
                    rotation="25 MB",
                    retention="10 days",
                )

            cls.set_debug(cls.__debug_on__)
            cls.set_trace(cls.__trace_on__)

    def __new__(
        cls,
        config: Optional["Config"] = None,
        level: Optional[int] = 40,
        debug: Optional[bool] = None,
        trace: Optional[bool] = None,
        record_log: Optional[bool] = None,
        logging_dir: Optional[str] = None,
    ):
        r"""Instantiate cybertensor logging system backend.
        Args:
            config (Config, optional):
                cybertensor.logging.config()
            level (int, optional):
                logger level (default: 40).
            debug (bool, optional):
                Turn on debug.
            trace (bool, optional):
                Turn on trace.
            record_log (bool, optional):
                If ``True``, logs are saved to logging dir.
            logging_dir (str, optional):
                Directory where logs are sunk.
        """

        cls.__has_been_inited__ = True

        if config is None:
            config = logging.config()
        config = copy.deepcopy(config)
        config.logging.debug = debug if debug is not None else config.logging.debug
        config.logging.trace = trace if trace is not None else config.logging.trace
        config.logging.record_log = (
            record_log if record_log is not None else config.logging.record_log
        )
        config.logging.logging_dir = (
            logging_dir if logging_dir is not None else config.logging.logging_dir
        )

        # Remove default sink.
        try:
            logger.remove(0)
        except Exception:
            pass

        # Optionally Remove other sinks.
        if cls.__std_sink__ is not None:
            logger.remove(cls.__std_sink__)
        if cls.__file_sink__ is not None:
            logger.remove(cls.__file_sink__)

        # Add filtered sys.stdout.
        cls.__std_sink__ = logger.add(
            sys.stdout,
            level=level,
            filter=cls.log_filter,
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            format=cls.log_formatter,
        )

        cls.set_debug(config.logging.debug)
        cls.set_trace(config.logging.trace)

        # ---- Setup logging to root ----
        if config.logging.record_log:
            filepath = config.logging.logging_dir + "/logs.log"
            cls.__file_sink__ = logger.add(
                filepath,
                filter=cls.log_save_filter,
                enqueue=True,
                backtrace=True,
                diagnose=True,
                format=cls.log_save_formatter,
                rotation="25 MB",
                retention="10 days",
            )

    @classmethod
    def config(cls):
        """Get config from the argument parser.

        Return:
            Config object
        """
        parser = argparse.ArgumentParser()
        logging.add_args(parser)
        return Config(parser, args=[])

    @classmethod
    def help(cls):
        """Print help to stdout"""
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        print(cls.__new__.__doc__)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: str = None):
        """Accept specific arguments fro parser"""
        prefix_str = "" if prefix is None else prefix + "."
        try:
            default_logging_debug = os.getenv("CT_LOGGING_DEBUG") or False
            default_logging_trace = os.getenv("CT_LOGGING_TRACE") or False
            default_logging_record_log = os.getenv("CT_LOGGING_RECORD_LOG") or False
            default_logging_logging_dir = (
                os.getenv("CT_LOGGING_LOGGING_DIR") or "~/.cybertensor/miners"
            )
            parser.add_argument(
                "--" + prefix_str + "logging.debug",
                action="store_true",
                help="""Turn on cybertensor debugging information""",
                default=default_logging_debug,
            )
            parser.add_argument(
                "--" + prefix_str + "logging.trace",
                action="store_true",
                help="""Turn on cybertensor trace level information""",
                default=default_logging_trace,
            )
            parser.add_argument(
                "--" + prefix_str + "logging.record_log",
                action="store_true",
                help="""Turns on logging to file.""",
                default=default_logging_record_log,
            )
            parser.add_argument(
                "--" + prefix_str + "logging.logging_dir",
                type=str,
                help="Logging default root directory.",
                default=default_logging_logging_dir,
            )
        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

    @classmethod
    def check_config(cls, config: "Config"):
        """Check config"""
        assert config.logging

    @classmethod
    def set_debug(cls, debug_on: bool = True):
        """Set debug for the specific cls class"""
        if not cls.__has_been_inited__:
            cls()
        cls.__debug_on__ = debug_on

    @classmethod
    def set_trace(cls, trace_on: bool = True):
        """Set trace back for the specific cls class"""
        if not cls.__has_been_inited__:
            cls()
        cls.__trace_on__ = trace_on

    @classmethod
    def get_level(cls) -> int:
        return 5 if cls.__trace_on__ else 10 if cls.__debug_on__ else 20

    @classmethod
    def log_filter(cls, record):
        """Filter out debug log if debug is not on"""
        if cls.get_level() <= record["level"].no:
            return True
        else:
            return False

    @classmethod
    def log_save_filter(cls, record):
        if cls.get_level() < record["level"].no:
            return True
        else:
            return False

    @classmethod
    def log_formatter(cls, record):
        """Log with different format according to record['extra']"""
        return "<blue>{time:YYYY-MM-DD HH:mm:ss.SSS}</blue> | <level>{level: ^16}</level> | {message}\n"

    @classmethod
    def log_save_formatter(cls, record):
        if cls.__trace_on__:
            return "{time:YYYY-MM-DD HH:mm:ss.SSS} | <level>{level: ^16}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {message}\n"
        else:
            return "{time:YYYY-MM-DD HH:mm:ss.SSS} | <level>{level: ^16}</level> | {message}\n"

    @classmethod
    def _format(cls, prefix: object, sufix: object = None):
        """Format logging message"""
        if isinstance(prefix, torch.Tensor):
            prefix = prefix.detach()
        if sufix is not None:
            if isinstance(sufix, torch.Tensor):
                sufix = "shape: {}".format(str(sufix.shape)) + " data: {}".format(
                    str(sufix.detach())
                )
            else:
                sufix = "{}".format(str(sufix))
        else:
            sufix = ""
        log_msg = str(prefix).ljust(30) + str(sufix)
        return _remove_loguru_ansi_directive(log_msg)

    @classmethod
    def success(cls, prefix: object, sufix: object = None):
        """Success logging"""
        if not cls.__has_been_inited__:
            cls()
        logger.success(cls._format(prefix, sufix))

    @classmethod
    def warning(cls, prefix: object, sufix: object = None):
        """Warning logging"""
        if not cls.__has_been_inited__:
            cls()
        logger.warning(cls._format(prefix, sufix))

    @classmethod
    def error(cls, prefix: object, sufix: object = None):
        """Error logging"""
        if not cls.__has_been_inited__:
            cls()
        logger.error(cls._format(prefix, sufix))

    @classmethod
    def info(cls, prefix: object, sufix: object = None):
        """Info logging"""
        if not cls.__has_been_inited__:
            cls()
        logger.info(cls._format(prefix, sufix))

    @classmethod
    def debug(cls, prefix: object, sufix: object = None):
        """Info logging"""
        if not cls.__has_been_inited__:
            cls()
        logger.debug(cls._format(prefix, sufix))

    @classmethod
    def trace(cls, prefix: object, sufix: object = None):
        """Info logging"""
        if not cls.__has_been_inited__:
            cls()
        logger.trace(cls._format(prefix, sufix))

    @classmethod
    def exception(cls, prefix: object, sufix: object = None):
        """Exception logging with traceback"""
        if not cls.__has_been_inited__:
            cls()
        logger.exception(cls._format(prefix, sufix))
