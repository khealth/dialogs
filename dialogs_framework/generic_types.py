from dataclasses import dataclass
from itertools import count

from typing import TypeVar, List, Union, Generic, Iterator
from .types import DialogStepNotDone, DialogStepDone, SendMessageFunction
from .dialog_state import DialogState

T = TypeVar("T")
ClientResponse = TypeVar("ClientResponse")
ServerMessage = TypeVar("ServerMessage")
ServerResponse = List[ServerMessage]
RunDialogReturnType = Union[DialogStepDone[T, ServerMessage], DialogStepNotDone[ServerMessage]]


@dataclass(frozen=True)
class DialogContext(Generic[ClientResponse, ServerMessage]):
    send: SendMessageFunction[ServerMessage]
    client_response: ClientResponse
    state: DialogState
    call_counter: Iterator[int]


def build_dialog_context(
    send: SendMessageFunction, client_response: ClientResponse, state: DialogState
) -> DialogContext:
    return DialogContext(
        send=send, client_response=client_response, state=state, call_counter=count()
    )
