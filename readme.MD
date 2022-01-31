<p align="center">
  <img width="300" height="300" src="https://user-images.githubusercontent.com/13794950/116088687-c41fc680-a6aa-11eb-8356-5242773c584e.png">
</p>

A Python library for resumable stateful functions.

## Resumable what now?

This framework is intended for long-lived backend flows, such as chatbot conversations. It allows one to write code as a chronological flow, and provides the magic to make execution resume where it left off.

Flows can be simple pre-programmed conversations, or complex user interactions with conditionals, loops, external APIs, and natural language processing. The aim of the framework is to reduce the complexity of managing execution state, and keeping track of where in the flow each user is located.

## Example

```python
# With the dialogs framework
@dialog()
def ask_a_name_dialog():
    run(send_message("What is your name?"))
    name = run(get_client_response())
    run(send_message(f"{name} is a beautiful name!"))

# No framework, manual state manipulation
def ask_a_name(client_answer, state):
    if not state.did_ask_already:
        state.did_ask_already = True
        name = client_answer
        return f"{name} is a beautiful name!"
    else:
        return "What is your name?"
```

## Philosophy

- No direct access to state.
- No breaks in the code flow with `return` statements.
- No in-memory state, scale-out friendly.

## Async safety

The framework uses `contextvars`, for the global context used by the functions `run` and `run_dialog`. It is not tested using gevent / greenlets, and compatibility may depend on the Python version as well.

## Running the examples

### Set up

To run the example, first install [poetry](https://python-poetry.org/docs/), and then run:

```bash
poetry install
```

### Guessbot

Launch the server by running:

```bash
poetry run uvicorn examples.guessbot.server.server_df:app --reload
```

Then run the client in a separate terminal:

```bash
poetry run python examples/guessbot/server/client.py
```

![image](https://user-images.githubusercontent.com/13794950/115526413-add3ce00-a298-11eb-9abd-ca779244fe13.png)

### Dragons

```bash
poetry run python -m examples.dragons.chat_example
```

## Generator based dialogs and Asyncio support

Starting from version 0.2.0 A new implementation of the dialogs exist. Instead of using `run` to define the resumable steps of the dialog you use a generator function `yield`, like this:

```python
@dialog()
def ask_a_name_dialog():
    yield send_message("What is your name?")
    name = yield get_client_response()
    yield send_message(f"{name} is a beautiful name!")
```

Such dialogs are then initiated with a call to `run_gen_dialog` instead of `run_dialog`.

Generator based dialogs provide allow for two improvements comparing to the `run` dialogs:

- The `contextvars` usage is dropped, which makes it more portable
- It allows using async io within a dialog

For example, this is now possible:

```python
@dialog()
async def ask_a_name_dialog():
    yield send_message("What is your name?")
    name = yield get_client_response()
    greeting = await call_some_api()
    yield send_message(f"{greeting} {name}!")
```

To be able to await on the dialog result, when using async io, use `run_async_gen_dialog` to initiate the dialog, which returns an awaitable.

## Generator based dialogs examples

### Guessbot

This examples uses asyncio.sleep to show how async io can be used in a dialog.

Launch the server by running:

```bash
poetry run uvicorn examples.guessbot.server.server_adf:app --reload
```

Then run the client in a separate terminal:

```bash
poetry run python examples/guessbot/server/client_async.py
```

### Dragons

```bash
poetry run python -m examples.dragons_gen.chat_example
```

# Contributing

This framework has been very recently open-sourced, and we are still learning the best way to collaborate. Please feel free to open issues and let us know if you find it useful.
