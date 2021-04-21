from random import randrange
from fastapi import FastAPI
from collections import defaultdict
from dialogs_framework import (
    dialog,
    InMemoryPersistence,
    run,
    run_dialog,
    send_message,
    get_client_response,
)


@dialog(version="1.1")
def game():
    run(send_message("Guess a number between 1 and 10."))
    correct_number = run(rand())

    while True:
        guess = run(get_client_response())
        if int(guess) == correct_number:
            break
        run(send_message("That's not it..."))

    run(send_message(f"Awesome! The number is {correct_number}"))
    run(send_message("Bye bye."))


@dialog()
def rand():
    return randrange(1, 11)


app = FastAPI()
state = defaultdict(InMemoryPersistence)


@app.post("/")
async def next_message(message, chat_id):
    persistence = state[chat_id]

    next_step = run_dialog(game(), persistence, message)
    return next_step.messages


subdialog_states = []
