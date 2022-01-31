from functools import partial
from typing import cast, Union, Optional, overload
from contextvars import ContextVar

from dialogs_framework.fallback_dialog import run_fallback_dialog

from .types import (
    Dialog,
    SendToClientException,
    get_client_response,
    send_message,
    DialogStepDone,
    DialogStepNotDone,
    SendMessageFunction,
    VersionMismatchException,
)
from .generic_types import ClientResponse, ServerMessage, T, DialogContext, build_dialog_context
from .persistence.persistence import PersistenceProvider
from .message_queue import MessageQueue


"""
This context is used to prevent having to pass arguments when calling dialogs_framework.
Its purpose is to make the syntax of defining dialogs_framework nicer.

It contains the context required by run() to call a subdialog.
"""
dialog_context: ContextVar[DialogContext] = ContextVar("dialog_context")

_InputDialogType = Union[get_client_response[T], Dialog[T]]
InputDialogType = Union[_InputDialogType, send_message[ServerMessage]]


def run_dialog(
    dialog: InputDialogType,
    persistence: PersistenceProvider,
    client_response: ClientResponse,
    fallback_dialog: Optional[InputDialogType] = None,
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

    dialog_context.set(build_dialog_context(send, client_response, state))

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
        return DialogStepDone(return_value=cast(T, return_value), messages=messages)
    else:
        return DialogStepNotDone(messages=messages)


_run_fallback_dialog = partial(run_fallback_dialog, run_dialog)


@overload
def run(subdialog: send_message[ServerMessage]) -> None:
    ...


@overload
def run(subdialog: _InputDialogType) -> T:
    ...


def run(subdialog: InputDialogType) -> Optional[T]:
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
    context: DialogContext = dialog_context.get()
    state = context.state
    client_response = context.client_response
    send = context.send
    call_counter = context.call_counter

    subdialog_state = state.get_subdialog_state(next(call_counter), subdialog)

    if subdialog.version != subdialog_state.version:
        raise VersionMismatchException

    if subdialog_state.is_done:
        return subdialog_state.return_value

    return_value: Optional[T]
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
        token = dialog_context.set(build_dialog_context(send, client_response, subdialog_state))
        return_value = subdialog.dialog()  # type: ignore
        dialog_context.reset(token)
    else:
        raise Exception("Unsupported dialog type")

    subdialog_state.return_value = return_value
    return return_value
