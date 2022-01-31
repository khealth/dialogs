from typing import Optional, Union, cast, overload
from functools import partial

from dialogs_framework.dialog_state import DialogState

from .types import (
    BaseDialog,
    GenDialog,
    send_message,
    get_client_response,
    DialogStepDone,
    ServerMessage,
    DialogStepNotDone,
    SendMessageFunction,
    SendToClientException,
    Dialog,
    VersionMismatchException,
)
from .message_queue import MessageQueue
from .persistence.persistence import PersistenceProvider
from .fallback_dialog import run_fallback_dialog

from .generic_types import T, ClientResponse, DialogContext, build_dialog_context


_GenInputDialogType = Union[get_client_response[T], Dialog[T], GenDialog[T]]
GenInputDialogType = Union[_GenInputDialogType, send_message[ServerMessage]]


def run_gen_dialog(
    dialog: GenInputDialogType,
    persistence: PersistenceProvider,
    client_response: ClientResponse,
    fallback_dialog: Optional[GenInputDialogType] = None,
) -> Union[DialogStepDone[T, ServerMessage], DialogStepNotDone[ServerMessage]]:
    """
    This is the interface for calling a generator based dialog from an external location.
    if the dialog or one of its subdialogs uses asyncio use run_async_gen_dialog instead.

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

    is_done = False
    try:
        return_value = _run_base_dialog(dialog, build_dialog_context(send, client_response, state))
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


_run_fallback_dialog = partial(run_fallback_dialog, run_gen_dialog)


@overload
def _run_base_dialog(subdialog: send_message[ServerMessage], context: DialogContext) -> None:
    ...


@overload
def _run_base_dialog(subdialog: _GenInputDialogType, context: DialogContext) -> T:
    ...


def _run_base_dialog(
    subdialog: GenInputDialogType,
    context: DialogContext,
) -> Optional[T]:
    state = context.state
    client_response = context.client_response
    send = context.send
    call_counter = context.call_counter

    subdialog_state = state.get_subdialog_state(next(call_counter), subdialog)

    if subdialog.version != subdialog_state.version:
        raise VersionMismatchException

    if subdialog_state.is_done:
        return subdialog_state.return_value

    return_value = run_gen_dialog_step(subdialog, subdialog_state, client_response, send)
    subdialog_state.return_value = return_value
    return return_value


def run_gen_dialog_step(
    step: BaseDialog[T],
    step_state: DialogState,
    client_response: ClientResponse,
    send: SendMessageFunction,
):
    return_value: Optional[T]
    if isinstance(step, get_client_response):
        if not step_state.sent_to_client:
            step_state.sent_to_client = True
            raise SendToClientException
        else:
            return_value = cast(T, client_response)
    elif isinstance(step, send_message):
        send(step.message)
        return_value = None
    elif isinstance(step, Dialog):
        return_value = step.dialog()  # type: ignore
    elif isinstance(step, GenDialog):
        return_value = _run_gen_dialog(
            step, build_dialog_context(send, client_response, step_state)
        )
    else:
        raise Exception("Unsupported dialog type")

    return return_value


def _run_gen_dialog(dialog: GenDialog[T], context: DialogContext) -> T:
    instance = dialog.dialog()  # type: ignore
    try:
        value_for_next_step = None
        while True:
            next_step = instance.send(value_for_next_step)
            value_for_next_step = _run_base_dialog(next_step, context)
    except StopIteration as ex:
        return ex.value
