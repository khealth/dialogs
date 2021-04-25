# Dialogs Framework
The Dialogs Framework is a Python library for writing resumable functions with persistent execution state.

# Examples

## Set up

To run the example, first install [poetry](https://python-poetry.org/docs/), and then run:
```bash
poetry install
```

## Guessbot
Launch the server by running:

```bash
poetry run uvicorn examples.guessbot.server.server_df:app --reload
```

Then run the client in a separate terminal:
```bash
poetry run python examples/guessbot/server/client.py
```

![image](https://user-images.githubusercontent.com/13794950/115526413-add3ce00-a298-11eb-9abd-ca779244fe13.png)

## Dragons
```bash
poetry run python -m examples.dragons.chat_example
```


# Async safety

The framework uses `contextvars`, for the global context used by the functions `run` and `run_dialog`. It is not tested using gevent / greenlets, and compatibility may depend on the Python version as well.