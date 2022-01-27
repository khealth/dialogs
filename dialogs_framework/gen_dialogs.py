from itertools import count
from typing import Optional, Union, cast

from dialogs_framework.dialog_state import DialogState

from .types import BaseDialog, send_message, get_client_response,DialogStepDone, ServerMessage, DialogStepNotDone, SendMessageFunction, SendToClientException, Dialog, VersionMismatchException
from .message_queue import MessageQueue
from .persistence.persistence import PersistenceProvider

from .dialogs import T, ClientResponse, DialogContext, RunDialogReturnType, ServerResponse

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
        return _run_fallback_gen_dialog(client_response, dialog, persistence, fallback_dialog, state)

    if dialog.version != state.version:
        state.reset(dialog, fallback_mode=True)
        return _run_fallback_gen_dialog(client_response, dialog, persistence, fallback_dialog, state)   
    if state.is_done:
        return state.return_value    

    is_done = False
    try:
        return_value = _run_base_dialog(dialog, state, send, client_response)
        is_done = True
    except VersionMismatchException:
        state.reset(dialog, fallback_mode=True)
        return _run_fallback_gen_dialog(client_response, dialog, persistence, fallback_dialog, state)        
    except SendToClientException:
        pass

    messages = queue.dequeue_all()
    persistence.save_state(state)
    if is_done:
        return DialogStepDone(return_value=return_value, messages=messages)
    else:
        return DialogStepNotDone(messages=messages)

def _run_base_dialog(base_dialog: BaseDialog[T], state: DialogState, send, client_response):
    if isinstance(base_dialog, get_client_response):
        if not state.sent_to_client:
            state.sent_to_client = True
            raise SendToClientException
        else:
            step_value = cast(T, client_response)
    elif isinstance(base_dialog, send_message):
        send(base_dialog.message)
        step_value = None
    elif isinstance(base_dialog, Dialog):
        subdialog_context =  DialogContext(
                state=state,
                client_response=client_response,
                send=send,
                call_counter=count(),
        )
        # recurse and return as next value
        step_value = _run_dialog(base_dialog, subdialog_context)
    else:
        raise Exception("Unsupported dialog type")

    return step_value

def _run_dialog(dialog: Dialog[T], context: DialogContext) -> T:
    state = context.state
    # TODO: support non gens as well
    instance = dialog.dialog()

    try:
        value_for_next_step = None
        while True:
            next_step = instance.send(value_for_next_step)
            next_step_state = state.get_subdialog_state(next(context.call_counter), next_step)
            if next_step.version != next_step_state.version:
                raise VersionMismatchException
            if next_step_state.is_done:
                value_for_next_step = next_step_state.return_value
            else:
                value_for_next_step = _run_base_dialog(next_step, next_step_state, context.send, context.client_response)
                next_step_state.return_value = value_for_next_step
    except StopIteration as ex:
        return ex.value

# This is (initially at least) a copy of the existing dialogs run_fallback...only its run_dialog is run_gen_dialog
# it should be possible to share most of the code, and pass through the dialog running function
def _run_fallback_gen_dialog(client_response, dialog, persistence, fallback_dialog, state):
    messages: ServerResponse = []
    if fallback_dialog is not None:
        next_step: RunDialogReturnType = run_gen_dialog(fallback_dialog, persistence, client_response)
        if not next_step.is_done:
            return next_step
        messages = next_step.messages
        # Fallback dialog completed
        state.reset(dialog, fallback_mode=False)

    next_step = run_gen_dialog(dialog, persistence, client_response, fallback_dialog)
    next_step.messages = messages + next_step.messages
    return next_step

