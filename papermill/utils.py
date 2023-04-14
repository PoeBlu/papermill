import os
import logging
import warnings

from contextlib import contextmanager
from functools import wraps

from .exceptions import PapermillParameterOverwriteWarning

logger = logging.getLogger('papermill.utils')


def merge_kwargs(caller_args, **callee_args):
    """Merge named argument.

    Function takes a dictionary of caller arguments and callee arguments as keyword arguments
    Returns a dictionary with merged arguments. If same argument is in both caller and callee
    arguments the last one will be taken and warning will be raised.

    Parameters
    ----------
    caller_args : dict
        Caller arguments
    **callee_args
        Keyword callee arguments

    Returns
    -------
    args : dict
       Merged arguments
    """
    if conflicts := set(caller_args) & set(callee_args):
        args = format(
            '; '.join([f'{key}={value}' for key, value in callee_args.items()])
        )
        msg = f"Callee will overwrite caller's argument(s): {args}"
        warnings.warn(msg, PapermillParameterOverwriteWarning)
    return dict(caller_args, **callee_args)


def remove_args(args=None, **kwargs):
    """Remove arguments from kwargs.

    Parameters
    ----------
    args : list
        Argument names to remove from kwargs
    **kwargs
        Arbitrary keyword arguments

    Returns
    -------
    kwargs : dict
       New dictionary of arguments
    """
    return {k: v for k, v in kwargs.items() if k not in args} if args else kwargs


# retry decorator
def retry(num):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            exception = None

            for i in range(num):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.debug('Retrying after: {}'.format(e))
                    exception = e
            else:
                raise exception

        return wrapper

    return decorate


@contextmanager
def chdir(path):
    """Change working directory to `path` and restore old path on exit.

    `path` can be `None` in which case this is a no-op.
    """
    if path is None:
        yield

    else:
        old_dir = os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(old_dir)
