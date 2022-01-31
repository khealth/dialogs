from dataclasses import dataclass
from typing import Optional, Union, cast, overload

from .types import (
    AsyncDialog,
    AsyncGenDialog,
    BaseDialog,
    GenDialog,
    DialogStepDone,
    ServerMessage,
    DialogStepNotDone,
    SendMessageFunction,
    SendToClientException,
    Dialog,
    VersionMismatchException,
    get_client_response,
    send_message,
)
from .message_queue import MessageQueue
from .persistence.persistence import PersistenceProvider

from .generic_types import (
    T,
    ClientResponse,
    DialogContext,
    RunDialogReturnType,
    ServerResponse,
    build_dialog_context,
)
from .dialog_state import DialogState

from .gen_dialogs import run_gen_dialog_step


@dataclass(frozen=True)
class dialog_result(BaseDialog[T]):
    value: T
    name: str = "dialog_result"
    version: str = "1.0"


_AsyncGenInputDialogType = Union[
    get_client_response[T], Dialog[T], GenDialog[T], AsyncDialog, AsyncGenDialog, dialog_result
]
AsyncGenInputDialogType = Union[_AsyncGenInputDialogType, send_message[ServerMessage]]


async def run_async_gen_dialog(
    dialog: AsyncGenInputDialogType,
    persistence: PersistenceProvider,
    client_response: ClientResponse,
    fallback_dialog: Optional[AsyncGenInputDialogType] = None,
) -> Union[DialogStepDone[T, ServerMessage], DialogStepNotDone[ServerMessage]]:
    """
    This is the interface for calling a generator based dialog from an external location.
    It returns an awaitable and allows running dialogs and subdialogs containg async io statements.

    The returned DialogStep object indicates:
    1. Whether the dialog is done
    2. If it's done, what the return value is
    3. If it's not done, what the next server messages are
    """

    queue = MessageQueue[ServerMessage]()
    send: SendMessageFunction = queue.enqueue

    state = persistence.get_state(dialog)
    if state.handling_fallback and fallback_dialog is not None:
        return await _run_fallback_dialog(
            client_response, dialog, persistence, fallback_dialog, state
        )

    is_done = False
    try:
        return_value = await _run_base_dialog(
            dialog, build_dialog_context(send, client_response, state)
        )
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
        return DialogStepDone(return_value=cast(T, return_value), messages=messages)
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


@overload
async def _run_base_dialog(subdialog: send_message[ServerMessage], context: DialogContext) -> None:
    ...


@overload
async def _run_base_dialog(
    subdialog: _AsyncGenInputDialogType,
    context: DialogContext,
) -> T:
    ...


async def _run_base_dialog(
    subdialog: AsyncGenInputDialogType,
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

    return_value: T
    if isinstance(subdialog, GenDialog):
        # for gen_dialog we still need to await, in case it has a subdialog that awaits
        return_value = await _run_gen_dialog(
            subdialog, build_dialog_context(send, client_response, subdialog_state)
        )
    elif isinstance(subdialog, AsyncDialog):
        return_value = await subdialog.dialog()  # type: ignore
    elif isinstance(subdialog, AsyncGenDialog):
        # async generators cannot return a value (https://www.python.org/dev/peps/pep-0525/#asynchronous-generators).
        # use yield to dialog_result keeping the result value for when this policy will change.
        return_value = await _run_async_gen_dialog(
            subdialog, build_dialog_context(send, client_response, subdialog_state)
        )
        if (
            subdialog_state.is_done
        ):  # if dialog_result was used then this is the actual value. stop here
            return subdialog_state.return_value
    elif isinstance(subdialog, dialog_result):
        # a solution for async generators not having return value, this step sets the
        # parent dialog value
        return_value = subdialog.value
        state.return_value = subdialog.value
    else:
        # the rest is executed in the same manner as regular gen dialogs
        return_value = run_gen_dialog_step(subdialog, subdialog_state, client_response, send)

    subdialog_state.return_value = return_value
    return return_value


async def _run_gen_dialog(dialog: GenDialog[T], context: DialogContext) -> T:
    instance = dialog.dialog()  # type: ignore
    try:
        value_for_next_step = None
        while True:
            next_step = instance.send(value_for_next_step)
            value_for_next_step = await _run_base_dialog(next_step, context)
    except StopIteration as ex:
        return ex.value


async def _run_async_gen_dialog(dialog: AsyncGenDialog[T], context: DialogContext):
    instance = dialog.dialog()  # type: ignore
    try:
        value_for_next_step = None
        while True:
            next_step = await instance.asend(value_for_next_step)
            value_for_next_step = await _run_base_dialog(next_step, context)
    except StopAsyncIteration:
        # async iterator does not return a value...so just return. use yield dialog_result
        # to setup a dialog result, instead
        pass
