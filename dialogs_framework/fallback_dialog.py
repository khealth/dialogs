from .dialog_state import DialogState
from .generic_types import RunDialogReturnType, ServerResponse


def run_fallback_dialog(
    run_dialog_func, client_response, dialog, persistence, fallback_dialog, state: DialogState
):
    messages: ServerResponse = []
    if fallback_dialog is not None:
        next_step: RunDialogReturnType = run_dialog_func(
            fallback_dialog, persistence, client_response
        )
        if not next_step.is_done:
            return next_step
        messages = next_step.messages
        # Fallback dialog completed
        state.reset(dialog, fallback_mode=False)

    next_step = run_dialog_func(dialog, persistence, client_response, fallback_dialog)
    next_step.messages = messages + next_step.messages
    return next_step
