from itertools import count
from typing import Iterator, TypeVar, List, cast, Union, Generic, Optional
from dataclasses import dataclass

from gevent.local import local

from .types import (
    Dialog,
    SendToClientException,
    get_client_response,
    send_message,
    DialogStepDone,
    DialogStepNotDone,
    BaseDialog,
    SendMessageFunction,
    VersionMismatchException,
)
from .persistence.persistence import PersistenceProvider
from .dialog_state import DialogState
from .message_queue import MessageQueue

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


# This is thread-safe, greenlet / gevent safe, but NOT asyncio safe
class ContextManager(local):
    context: DialogContext


dialog_context: ContextManager = ContextManager()


"""
This context is used to prevent having to pass arguments when calling dialogs_framework.
Its purpose is to make the syntax of defining dialogs_framework nicer.

It contains the context required by run() to call a subdialog.
"""


def run_dialog(
    dialog: BaseDialog[T],
    persistence: PersistenceProvider,
    client_response: ClientResponse,
    fallback_dialog: Optional[BaseDialog[T]] = None,
) -> Union[DialogStepDone[T, ServerMessage], DialogStepNotDone[ServerMessage]]:
    """
    This is the interface for calling a dialog from an external location.

    The returned DialogStep object indicates:
    1. Whether the dialog is done
    2. If it's done, what the return value is
    3. If it's not done, what the next server messages are
    """
    queue = MessageQueue[ServerMessage]()
    send: SendMessageFunction = queue.enqueue

    state = persistence.get_state(dialog)
    if state.handling_fallback and fallback_dialog is not None:
        return _run_fallback_dialog(client_response, dialog, persistence, fallback_dialog, state)

    dialog_context.context = DialogContext(
        send=send, state=state, call_counter=count(), client_response=client_response
    )

    is_done = False
    try:
        return_value = run(dialog)
        is_done = True
    except VersionMismatchException:
        state.reset(dialog, fallback_mode=True)
        return _run_fallback_dialog(client_response, dialog, persistence, fallback_dialog, state)

    except SendToClientException:
        pass

    messages = queue.dequeue_all()
    persistence.save_state(state)
    if is_done:
        return DialogStepDone(return_value=return_value, messages=messages)
    else:
        return DialogStepNotDone(messages=messages)


def _run_fallback_dialog(client_response, dialog, persistence, fallback_dialog, state):
    messages: ServerResponse = []
    if fallback_dialog is not None:
        next_step: RunDialogReturnType = run_dialog(fallback_dialog, persistence, client_response)
        if not next_step.is_done:
            return next_step
        messages = next_step.messages
        # Fallback dialog completed
        state.reset(dialog, fallback_mode=False)

    next_step = run_dialog(dialog, persistence, client_response, fallback_dialog)
    next_step.messages = messages + next_step.messages
    return next_step


def run(subdialog: BaseDialog[T]) -> T:
    """
    This function wraps the execution of all subdialogs.

    It does the following:
    1. If the dialog is done, return its saved return_value without running it again.

    2. If not, run the dialog.

       The two primitives (get_client_response, send_message) have their own special logic:
           * get_client_response raises a SendToClientException, which is caught by run_dialog
             and returns control to the calling component.

           * send_message adds a message to the outgoing message queue.

       Normal dialogs_framework accept the _run function itself, which allows them to call their
       own subdialogs. Their _run is injected with their appropriate state.

    3. If there are no more messages to send, set the return value in the DialogState
       and return it.
    """
    context: DialogContext = dialog_context.context
    state = context.state
    client_response = context.client_response
    send = context.send
    call_counter = context.call_counter

    subdialog_state = state.get_subdialog_state(next(call_counter), subdialog)

    if subdialog.version != subdialog_state.version:
        raise VersionMismatchException

    if subdialog_state.is_done:
        return subdialog_state.return_value

    return_value: T
    if isinstance(subdialog, get_client_response):
        if not subdialog_state.sent_to_client:
            subdialog_state.sent_to_client = True
            raise SendToClientException
        else:
            return_value = cast(T, client_response)
    elif isinstance(subdialog, send_message):
        send(subdialog.message)
        return_value = None
    elif isinstance(subdialog, Dialog):
        # This token is used to return to the parent context after
        # the subdialog has finished its execution.
        parent_context = dialog_context.context
        dialog_context.context = DialogContext(
            state=subdialog_state, client_response=client_response, send=send, call_counter=count()
        )
        return_value = subdialog.dialog()  # type: ignore
        dialog_context.context = parent_context
    else:
        raise Exception("Unsupported dialog type")

    subdialog_state.return_value = return_value
    return return_value
