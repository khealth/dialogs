from itertools import count
import inspect
from typing import Counter, Optional, Union, cast
from functools import partial

from dialogs_framework.dialog_state import DialogState

from .types import (
    BaseDialog,
    dialog,
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

from .generic_types import T, ClientResponse, DialogContext


# this is now VERY similar to run_dialog of dialogs...maybe i can refactor
def run_gen_dialog(
    dialog: Dialog[T],
    persistence: PersistenceProvider,
    client_response: ClientResponse,
    fallback_dialog: Optional[Dialog[T]] = None,
) -> Union[DialogStepDone[T, ServerMessage], DialogStepNotDone[ServerMessage]]:
    queue = MessageQueue[ServerMessage]()
    send: SendMessageFunction = queue.enqueue

    state = persistence.get_state(dialog)
    if state.handling_fallback and fallback_dialog is not None:
        return _run_fallback_dialog(client_response, dialog, persistence, fallback_dialog, state)

    context = DialogContext(
        send=send, state=state, call_counter=count(), client_response=client_response
    )

    is_done = False
    try:
        return_value = _run_base_dialog(dialog, context)
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


_run_fallback_dialog = partial(run_fallback_dialog, run_gen_dialog)

#  this is now VERY similar to run of dialogs...maybe i can refactor
def _run_base_dialog(subdialog: BaseDialog[T], context: DialogContext) -> T:
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
        subdialog_context = DialogContext(
            state=subdialog_state,
            client_response=client_response,
            send=send,
            call_counter=count(),
        )
        return_value = _run_dialog(subdialog, subdialog_context)
    else:
        raise Exception("Unsupported dialog type")

    subdialog_state.return_value = return_value
    return return_value


def _run_dialog(dialog: Dialog[T], context: DialogContext) -> T:
    result = dialog.dialog()
    if inspect.isgenerator(result):
        instance = result
        try:
            value_for_next_step = None
            while True:
                next_step = instance.send(value_for_next_step)
                value_for_next_step = _run_base_dialog(next_step, context)
        except StopIteration as ex:
            return ex.value
    else:
        return result
