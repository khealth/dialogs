import inspect
import asyncio

from typing import Generic, TypeVar, Callable, List, Generator, Union, Awaitable, AsyncGenerator
from typing_extensions import Protocol, Literal
from dataclasses import dataclass

T = TypeVar("T", covariant=True)
ServerMessage = TypeVar("ServerMessage", contravariant=True)


class BaseDialog(Generic[T]):
    version: str
    name: str


class get_client_response(BaseDialog[T]):
    name: str = "get_client_response"
    version: str = "1.0"


@dataclass
class send_message(BaseDialog[None], Generic[ServerMessage]):
    message: ServerMessage
    name: str = "send_message"
    version: str = "1.0"


@dataclass(frozen=True)
class Dialog(BaseDialog[T]):
    dialog: Callable[[], T]
    version: str
    name: str


@dataclass(frozen=True)
class GenDialog(BaseDialog[T]):
    dialog: Callable[[], Generator[BaseDialog[T], T, T]]
    version: str
    name: str


@dataclass(frozen=True)
class AsyncDialog(BaseDialog[T]):
    dialog: Callable[[], Awaitable[T]]
    version: str
    name: str


@dataclass(frozen=True)
class AsyncGenDialog(BaseDialog[T]):
    dialog: Callable[[], AsyncGenerator[BaseDialog[T], T]]
    version: str
    name: str


class SendToClientException(Exception):
    pass


class VersionMismatchException(Exception):
    """
    Raised when dialogs_framework have mismatching versions.
    This exception is used to break out of the currently running dialog
    and handle the mismatch on the parent run_dialog.
    """

    pass


def dialog(version: str = "1.0"):
    """
    This decorator wraps any function and turns it into a dialog, i.e.
    an object you can call with run(), for dialogs or yield for generator dialogs.

    When you call the wrapped function f, with its parameters, it gets
    packaged as a closure inside a Dialog class. This is necessary
    because we do not want the function to run immediately, but only
    when called by run().
    """

    def decorator(
        f: Callable[..., T]
    ) -> Callable[..., Union[Dialog[T], GenDialog[T], AsyncGenDialog[T], AsyncDialog[T]]]:
        def wrapper(*args, **kwargs):
            def f_closure() -> T:
                return f(*args, **kwargs)

            if inspect.isasyncgenfunction(f):
                return AsyncGenDialog(version=version, name=f.__name__, dialog=f_closure)

            if asyncio.iscoroutinefunction(f):
                return AsyncDialog(version=version, name=f.__name__, dialog=f_closure)

            if inspect.isgeneratorfunction(f):
                return GenDialog(version=version, name=f.__name__, dialog=f_closure)

            return Dialog(version=version, name=f.__name__, dialog=f_closure)

        return wrapper

    return decorator


class SendMessageFunction(Protocol[ServerMessage]):
    def __call__(self, message: ServerMessage) -> None:
        ...


@dataclass
class DialogStepDone(Generic[T, ServerMessage]):
    return_value: T
    messages: List[ServerMessage]
    is_done: Literal[True] = True


@dataclass
class DialogStepNotDone(Generic[ServerMessage]):
    messages: List[ServerMessage]
    is_done: Literal[False] = False


class DialogStateException(Exception):
    pass
