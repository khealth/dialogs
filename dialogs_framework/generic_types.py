from dataclasses import dataclass

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
