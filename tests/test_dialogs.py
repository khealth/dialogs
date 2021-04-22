from concurrent.futures.thread import ThreadPoolExecutor
from time import sleep

import gevent
from gevent import time
from typing import Tuple

from dialogs_framework.dialogs import run_dialog, run
from dialogs_framework.types import dialog, send_message, get_client_response, DialogStepDone
from dialogs_framework.persistence.in_memory import InMemoryPersistence, PersistenceProvider


@dialog(version="1.0")
def name_getter_dialog() -> str:
    run(send_message("Hello."))
    run(send_message("Nice to meet you!"))
    run(send_message("what is your name?"))
    return run(get_client_response())


@dialog(version="1.1")
def name_getter_dialog_take_2() -> str:
    run(send_message("Tell me your name! Now!!!"))
    return run(get_client_response())


@dialog(version="1.0")
def versioned_subdialog() -> str:
    run(send_message("I am a dialog"))
    return run(get_client_response())


@dialog(version="1.1")
def versioned_subdialog_take_2() -> str:
    run(send_message("I have a different version, HA! HA! HA!"))
    return run(get_client_response())


@dialog(version="1.0")
def dialog_with_subdialog() -> str:
    run(versioned_subdialog())
    return run(get_client_response())


@dialog(version="1.0")
def dialog_with_subdialog_take_2() -> str:
    run(versioned_subdialog_take_2())
    return run(get_client_response())


@dialog(version="1.0")
def name_getter_dialog_take_3() -> str:
    run(send_message("I need to know your name"))
    name: str = run(get_client_response())
    run(send_message("Wait! i have another message for you!"))
    return name


@dialog(version="1.0")
def fallback_without_client_response() -> None:
    run(send_message("Falling back!"))


@dialog(version="1.0")
def fallback_with_client_response() -> None:
    run(send_message("Falling back!"))
    run(get_client_response())
    run(send_message("Get up fool"))


@dialog(version="1.0")
def topic_dialog() -> Tuple[str, str]:
    name = run(name_getter_dialog())
    run(send_message(f"Hi {name}!"))
    run(send_message("What would you like to talk about"))
    topic: str = run(get_client_response())
    return name, topic


def run_echo_dialog_task(message: str):
    persistence: PersistenceProvider = InMemoryPersistence()
    test_dialog = echo_dialog(message)
    next_step = run_dialog(test_dialog, persistence, "test")  # type: ignore

    assert len(next_step.messages) == 1

    return next_step.messages[0]


@dialog(version="test")
def echo_dialog(message: str):
    # Release greenlet
    time.sleep(0)
    # Release thread
    sleep(0.0001)
    run(send_message(message))


def test_run_dialog_happy_flow():
    persistence = InMemoryPersistence()

    step1 = run_dialog(name_getter_dialog(), persistence, "")
    assert not step1.is_done
    assert len(step1.messages) == 3

    step2 = run_dialog(name_getter_dialog(), persistence, "Johnny")
    assert step2.is_done
    assert step2.return_value == "Johnny"


def test_run_dialog_with_subdialog_happy_flow():
    persistence = InMemoryPersistence()
    step1 = run_dialog(topic_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = run_dialog(topic_dialog(), persistence, "Johnny")
    assert len(step2.messages) == 2
    assert step2.messages[0] == "Hi Johnny!"

    step3 = run_dialog(topic_dialog(), persistence, "Peanuts")
    assert step3.is_done
    assert step3.return_value == ("Johnny", "Peanuts")


def test_run_dialog_raise_exception_changed_version():
    persistence = InMemoryPersistence()
    step1 = run_dialog(name_getter_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = run_dialog(name_getter_dialog_take_2(), persistence, "Johnny")
    assert step2.messages == ["Tell me your name! Now!!!"]
    assert not step2.is_done


def test_run_dialog_with_fallback_without_client_response():
    persistence = InMemoryPersistence()
    step1 = run_dialog(name_getter_dialog(), persistence, "", fallback_without_client_response())
    assert step1.messages == ["Hello.", "Nice to meet you!", "what is your name?"]

    step2 = run_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    assert step2.messages == ["Falling back!", "Tell me your name! Now!!!"]

    step3 = run_dialog(
        name_getter_dialog_take_2(), persistence, "Johnny", fallback_without_client_response()
    )
    assert step3.is_done
    assert step3.return_value == "Johnny"


def test_run_dialog_with_fallback_with_client_response():
    persistence = InMemoryPersistence()
    step1 = run_dialog(name_getter_dialog(), persistence, "", fallback_with_client_response())
    assert len(step1.messages) == 3

    step2 = run_dialog(
        name_getter_dialog_take_2(), persistence, "Juanito", fallback_with_client_response()
    )
    assert step2.messages == ["Falling back!"]
    # We don't test for the return value of this part because we don't handle the internal fallback dialogs_framework return_value

    step3 = run_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_with_client_response()
    )
    assert step3.messages == ["Get up fool", "Tell me your name! Now!!!"]

    step4 = run_dialog(
        name_getter_dialog_take_2(), persistence, "Johnny", fallback_with_client_response()
    )
    assert step4.is_done
    assert step4.return_value == "Johnny"


def test_run_dialog_with_fallback_on_subdialog_version_mismatch():
    persistence = InMemoryPersistence()
    step1 = run_dialog(dialog_with_subdialog(), persistence, "", fallback_without_client_response())
    assert step1.messages == ["I am a dialog"]

    step2 = run_dialog(
        dialog_with_subdialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    assert step2.messages == ["Falling back!", "I have a different version, HA! HA! HA!"]


def test_run_dialog_with_fallback_truncates_leftover_messages():
    persistence = InMemoryPersistence()
    step1 = run_dialog(
        name_getter_dialog_take_3(), persistence, "", fallback_with_client_response()
    )
    assert step1.messages == ["I need to know your name"]

    step2 = run_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    # We expect the second message of `name_getter_dialog_take_3` not to be here
    assert step2.messages == ["Falling back!", "Tell me your name! Now!!!"]


def test_run_dialog_returns_leftover_messages_when_done():
    persistence = InMemoryPersistence()
    next_step = run_dialog(send_message("what is your name?"), persistence, "")

    assert next_step.is_done
    assert next_step.messages == ["what is your name?"]


def test_running_dialogs_concurrently_handles_messages_apart():
    messages = ["first", "second", "third"]
    executor = ThreadPoolExecutor(max_workers=len(messages))

    jobs = [executor.submit(run_echo_dialog_task, message) for message in messages]
    results = [job.result() for job in jobs]

    assert results == messages


def test_running_two_dialogs_concurrently_with_gevent_doesnt_mix_messages():
    messages = ["first", "second", "third"]

    jobs = [gevent.spawn(run_echo_dialog_task, message) for message in messages]
    gevent.joinall(jobs)
    results = [result.value for result in jobs]

    assert results == messages
