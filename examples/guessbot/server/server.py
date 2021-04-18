from random import randrange
from fastapi import FastAPI
from dataclasses import dataclass
from typing import Optional
from collections import defaultdict


@dataclass
class GameState:
    is_first_message: bool = True
    is_done: bool = False
    correct_number: Optional[int] = None


states = defaultdict(GameState)
app = FastAPI()


@app.post("/")
async def next_message(message, chat_id):
    state = states[chat_id]

    if state.is_done:
        return []

    if state.is_first_message:
        state.correct_number = randrange(1, 11)
        state.is_first_message = False
        return ["Guess a number between 1 and 10."]

    if int(message) != state.correct_number:
        return ["That's not it..."]

    state.is_done = True
    return [f"Awesome! The number is {state.correct_number}", "Bye bye."]
