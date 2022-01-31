from typing import List, cast, Union

from dialogs_framework import GenDialog, Dialog, send_message, get_client_response, dialog


@dialog(version="1.0")
def prompt(text):
    yield send_message(text)
    response = yield get_client_response()
    return cast(str, response)


@dialog(version="1.0")
def chain(dialogs: List[Union[GenDialog, Dialog, send_message, get_client_response]]):
    for dialog in dialogs:
        yield dialog


@dialog(version="1.0")
def multichoice(question: str, wrong_answer_prompt: str, choices: List[str]):
    first_time = True

    while True:
        message = question if first_time else wrong_answer_prompt
        text = "\n".join([message] + [f"{i+1}. {choice}" for i, choice in enumerate(choices)])
        answer = yield prompt(text)

        valid_answers = {str(i + 1) for i in range(len(choices))}
        if answer in valid_answers:
            return int(answer) - 1

        first_time = False


@dialog(version="1.0")
def yes_no(question: str, wrong_answer_prompt: str):
    first_time = True

    while True:
        message = question if first_time else wrong_answer_prompt
        raw_answer = yield prompt(message)
        answer = raw_answer.strip().lower()

        valid_answer_values = {"n": False, "no": False, "y": True, "yes": True}
        if answer in valid_answer_values:
            return valid_answer_values[answer]

        first_time = False
