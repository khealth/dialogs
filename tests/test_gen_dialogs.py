from typing import Tuple
from time import sleep
from concurrent.futures.thread import ThreadPoolExecutor

from dialogs_framework.persistence.persistence import PersistenceProvider
from dialogs_framework.persistence.in_memory import InMemoryPersistence
from dialogs_framework.types import dialog, send_message, get_client_response
from dialogs_framework.gen_dialogs import run_gen_dialog


@dialog(version="1.0")
def fallback_without_client_response() -> None:
    yield send_message("Falling back!")


@dialog(version="1.0")
def name_getter_dialog() -> str:
    yield send_message("Hello.")
    yield send_message("Nice to meet you!")
    yield send_message("what is your name?")
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def topic_dialog() -> Tuple[str, str]:
    name = yield name_getter_dialog()
    yield send_message(f"Hi {name}!")
    yield send_message("What would you like to talk about")
    topic = yield get_client_response()
    return name, topic


@dialog(version="1.1")
def name_getter_dialog_take_2() -> str:
    yield send_message("Tell me your name! Now!!!")
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def fallback_with_client_response() -> None:
    yield send_message("Falling back!")
    yield get_client_response()
    yield send_message("Get up fool")


@dialog(version="1.0")
def versioned_subdialog() -> str:
    yield send_message("I am a dialog")
    result = yield get_client_response()
    return result


@dialog(version="1.1")
def versioned_subdialog_take_2() -> str:
    yield send_message("I have a different version, HA! HA! HA!")
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def dialog_with_subdialog() -> str:
    yield versioned_subdialog()
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def dialog_with_subdialog_take_2() -> str:
    yield versioned_subdialog_take_2()
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def name_getter_dialog_take_3() -> str:
    yield send_message("I need to know your name")
    name = yield get_client_response()
    yield send_message("Wait! i have another message for you!")
    return name


@dialog(version="test")
def echo_dialog(message: str):
    # Release thread
    sleep(0.0001)
    yield send_message(message)


def run_echo_dialog_task(message: str):
    persistence: PersistenceProvider = InMemoryPersistence()
    test_dialog = echo_dialog(message)
    next_step = run_gen_dialog(test_dialog, persistence, "test")  # type: ignore

    assert len(next_step.messages) == 1

    return next_step.messages[0]


@dialog(version="1.0")
def no_yield_dialog() -> str:
    return "hello!"


@dialog(version="1.0")
def dialog_with_no_yield_subdialog() -> str:
    next_message = yield no_yield_dialog()
    yield send_message(next_message)
    result = yield get_client_response()
    return result


def test_run_dialog_happy_flow():
    persistence = InMemoryPersistence()

    step1 = run_gen_dialog(name_getter_dialog(), persistence, "")
    assert not step1.is_done
    assert len(step1.messages) == 3

    step2 = run_gen_dialog(name_getter_dialog(), persistence, "Johnny")
    assert step2.is_done
    assert step2.return_value == "Johnny"


def test_run_dialog_with_subdialog_happy_flow():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(topic_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = run_gen_dialog(topic_dialog(), persistence, "Johnny")
    assert len(step2.messages) == 2
    assert step2.messages[0] == "Hi Johnny!"

    step3 = run_gen_dialog(topic_dialog(), persistence, "Peanuts")
    assert step3.is_done
    assert step3.return_value == ("Johnny", "Peanuts")


def test_run_dialog_raise_exception_changed_version():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(name_getter_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = run_gen_dialog(name_getter_dialog_take_2(), persistence, "Johnny")
    assert step2.messages == ["Tell me your name! Now!!!"]
    assert not step2.is_done


def test_run_dialog_with_fallback_without_client_response():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(
        name_getter_dialog(), persistence, "", fallback_without_client_response()
    )
    assert step1.messages == ["Hello.", "Nice to meet you!", "what is your name?"]

    step2 = run_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    assert step2.messages == ["Falling back!", "Tell me your name! Now!!!"]

    step3 = run_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Johnny", fallback_without_client_response()
    )
    assert step3.is_done
    assert step3.return_value == "Johnny"


def test_run_dialog_with_fallback_with_client_response():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(name_getter_dialog(), persistence, "", fallback_with_client_response())
    assert len(step1.messages) == 3

    step2 = run_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Juanito", fallback_with_client_response()
    )
    assert step2.messages == ["Falling back!"]
    # We don't test for the return value of this part because we don't handle the internal fallback dialogs_framework return_value

    step3 = run_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_with_client_response()
    )
    assert step3.messages == ["Get up fool", "Tell me your name! Now!!!"]

    step4 = run_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Johnny", fallback_with_client_response()
    )
    assert step4.is_done
    assert step4.return_value == "Johnny"


def test_run_dialog_with_fallback_on_subdialog_version_mismatch():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(
        dialog_with_subdialog(), persistence, "", fallback_without_client_response()
    )
    assert step1.messages == ["I am a dialog"]

    step2 = run_gen_dialog(
        dialog_with_subdialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    assert step2.messages == ["Falling back!", "I have a different version, HA! HA! HA!"]


def test_run_dialog_with_fallback_truncates_leftover_messages():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(
        name_getter_dialog_take_3(), persistence, "", fallback_with_client_response()
    )
    assert step1.messages == ["I need to know your name"]

    step2 = run_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    # We expect the second message of `name_getter_dialog_take_3` not to be here
    assert step2.messages == ["Falling back!", "Tell me your name! Now!!!"]


def test_run_dialog_returns_leftover_messages_when_done():
    persistence = InMemoryPersistence()
    next_step = run_gen_dialog(send_message("what is your name?"), persistence, "")

    assert next_step.is_done
    assert next_step.messages == ["what is your name?"]


def test_running_dialogs_concurrently_handles_messages_apart():
    messages = ["first", "second", "third"]
    executor = ThreadPoolExecutor(max_workers=len(messages))

    jobs = [executor.submit(run_echo_dialog_task, message) for message in messages]
    results = [job.result() for job in jobs]

    assert results == messages


def test_dialog_with_no_steps():
    persistence = InMemoryPersistence()

    next_step = run_gen_dialog(no_yield_dialog(), persistence, "")
    assert next_step.is_done
    assert next_step.return_value == "hello!"


def test_dialog_with_no_steps_as_subdialog():
    persistence = InMemoryPersistence()
    step1 = run_gen_dialog(dialog_with_no_yield_subdialog(), persistence, "")
    assert step1.messages == ["hello!"]
    assert not step1.is_done

    step2 = run_gen_dialog(dialog_with_no_yield_subdialog(), persistence, "Julia")
    assert step2.is_done
    assert step2.return_value == "Julia"
