from typing import Generic, TypeVar, Callable, List
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
    an object you can call with run().

    When you call the wrapped function f, with its parameters, it gets
    packaged as a closure inside a Dialog class. This is necessary
    because we do not want the function to run immediately, but only
    when called by run().
    """

    def decorator(f: Callable[..., T]) -> Callable[..., Dialog[T]]:
        def wrapper(*args, **kwargs) -> Dialog[T]:
            def f_closure() -> T:
                return f(*args, **kwargs)

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
