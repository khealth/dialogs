# Dialogs Framework
The Dialogs Framework is a Python library for writing resumable functions with persistent execution state.

## Resumable what now?
This framework is intended for long-lived backend flows, such as chatbot conversations. It allows one to write code as a chronological flow, and provides the magic to make execution resume where it left off.

## Code sample
```python
# No dialog, manual state manipulation
def ask_a_name(client_answer, state):
    if not state.did_ask_already:
        state.did_ask_already = True
        name = client_answer
        return f"{name} is a beautiful name!"
    else:
        return "What is your name?"

# With the dialogs framework
@dialog()
def ask_a_name_dialog():
    run(send_message("What is your name?"))
    name = run(get_client_response())
    run(send_message(f"{name} is a beautiful name!"))
```

## Philosophy
* No direct access to flow state.
* No breaks in the flow with `return` statements.
* No in-memory state, scale-out friendly.

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

# Contributing
This framework has been very recently open-sourced, and we are still learning the best way to collaborate. Please feel free to open issues and let us know if you find it useful.