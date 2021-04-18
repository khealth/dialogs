from typing import List, Any, cast

from dialogs import BaseDialog, send_message, get_client_response, dialog, run


@dialog(version="1.0")
def prompt(text) -> str:
    run(send_message(text))
    response: str = run(get_client_response())
    return cast(str, response)


@dialog(version="1.0")
def chain(dialogs: List[BaseDialog]) -> List[Any]:
    return [run(dialog) for dialog in dialogs]


@dialog(version="1.0")
def multichoice(question: str, wrong_answer_prompt: str, choices: List[str]) -> int:
    first_time = True

    while True:
        message = question if first_time else wrong_answer_prompt
        text = "\n".join([message] + [f"{i+1}. {choice}" for i, choice in enumerate(choices)])
        answer = run(prompt(text))

        valid_answers = {str(i + 1) for i in range(len(choices))}
        if answer in valid_answers:
            return int(answer) - 1

        first_time = False


@dialog(version="1.0")
def yes_no(question: str, wrong_answer_prompt: str) -> bool:
    first_time = True

    while True:
        message = question if first_time else wrong_answer_prompt
        raw_answer = run(prompt(message))
        answer = raw_answer.strip().lower()

        valid_answer_values = {"n": False, "no": False, "y": True, "yes": True}
        if answer in valid_answer_values:
            return valid_answer_values[answer]

        first_time = False
