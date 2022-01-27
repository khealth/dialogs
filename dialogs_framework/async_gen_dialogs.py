from itertools import count
from typing import Optional, Union, cast

from .types import (
    AsyncDialog,
    AsyncGenDialog,
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

from .generic_types import T, ClientResponse, DialogContext, RunDialogReturnType, ServerResponse
from .dialog_state import DialogState

# this is now VERY similar to run_dialog of dialogs...maybe i can refactor
async def run_async_gen_dialog(
    dialog: BaseDialog[T],
    persistence: PersistenceProvider,
    client_response: ClientResponse,
    fallback_dialog: Optional[Dialog[T]] = None,
) -> Union[DialogStepDone[T, ServerMessage], DialogStepNotDone[ServerMessage]]:
    queue = MessageQueue[ServerMessage]()
    send: SendMessageFunction = queue.enqueue

    state = persistence.get_state(dialog)
    if state.handling_fallback and fallback_dialog is not None:
        return await _run_fallback_dialog(
            client_response, dialog, persistence, fallback_dialog, state
        )

    context = DialogContext(
        send=send, state=state, call_counter=count(), client_response=client_response
    )

    is_done = False
    try:
        return_value = await _run_base_dialog(dialog, context)
        is_done = True
    except VersionMismatchException:
        state.reset(dialog, fallback_mode=True)
        return await _run_fallback_dialog(
            client_response, dialog, persistence, fallback_dialog, state
        )

    except SendToClientException:
        pass

    messages = queue.dequeue_all()
    persistence.save_state(state)
    if is_done:
        return DialogStepDone(return_value=return_value, messages=messages)
    else:
        return DialogStepNotDone(messages=messages)


async def _run_fallback_dialog(
    client_response, dialog, persistence, fallback_dialog, state: DialogState
):
    messages: ServerResponse = []
    if fallback_dialog is not None:
        next_step: RunDialogReturnType = await run_async_gen_dialog(
            fallback_dialog, persistence, client_response
        )
        if not next_step.is_done:
            return next_step
        messages = next_step.messages
        # Fallback dialog completed
        state.reset(dialog, fallback_mode=False)

    next_step = await run_async_gen_dialog(dialog, persistence, client_response, fallback_dialog)
    next_step.messages = messages + next_step.messages
    return next_step


#  this is now VERY similar to run of dialogs...maybe i can refactor
async def _run_base_dialog(subdialog: BaseDialog[T], context: DialogContext) -> T:
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
        return_value = subdialog.dialog()
    elif isinstance(subdialog, GenDialog):
        subdialog_context = DialogContext(
            state=subdialog_state,
            client_response=client_response,
            send=send,
            call_counter=count(),
        )
        return_value = await _run_gen_dialog(subdialog, subdialog_context)
    elif isinstance(subdialog, AsyncDialog):
        return_value = await subdialog.dialog()
    elif isinstance(subdialog, AsyncGenDialog):
        subdialog_context = DialogContext(
            state=subdialog_state,
            client_response=client_response,
            send=send,
            call_counter=count(),
        )
        return_value = await _run_async_gen_dialog(subdialog, subdialog_context)
    else:
        raise Exception("Unsupported dialog type")

    subdialog_state.return_value = return_value
    return return_value


async def _run_gen_dialog(dialog: GenDialog[T], context: DialogContext) -> T:
    instance = dialog.dialog()
    try:
        value_for_next_step = None
        while True:
            next_step = instance.send(value_for_next_step)
            value_for_next_step = await _run_base_dialog(next_step, context)
    except StopIteration as ex:
        return ex.value


async def _run_async_gen_dialog(dialog: AsyncGenDialog[T], context: DialogContext) -> T:
    instance = dialog.dialog()
    try:
        value_for_next_step = None
        while True:
            next_step = await instance.asend(value_for_next_step)
            value_for_next_step = await _run_base_dialog(next_step, context)
    except StopAsyncIteration as ex:
        return ex.value