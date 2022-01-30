import asyncio
from random import randrange
from fastapi import FastAPI
from collections import defaultdict
from dialogs_framework import (
    dialog,
    InMemoryPersistence,
    run_async_gen_dialog,
    send_message,
    get_client_response,
)


@dialog(version="1.1")
async def sleep_a_bit(how_much):
    await asyncio.sleep(how_much)


@dialog(version="1.1")
def game():
    yield send_message("Guess a number between 1 and 10.")
    correct_number = yield rand()

    while True:
        guess = yield get_client_response()
        if int(guess) == correct_number:
            yield sleep_a_bit(1)
            break
        yield sleep_a_bit(5)
        yield send_message("That's not it...")

    yield send_message(f"Awesome! The number is {correct_number}")
    yield send_message("Bye bye.")


@dialog()
def rand():
    return randrange(1, 11)


app = FastAPI()
state = defaultdict(InMemoryPersistence)


@app.post("/async")
async def next_message(message, chat_id):
    persistence = state[chat_id]

    next_step = await run_async_gen_dialog(game(), persistence, message)
    return next_step.messages


subdialog_states = []
