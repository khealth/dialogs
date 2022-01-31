import pytest
import asyncio
from typing import Tuple
from time import sleep

from dialogs_framework.persistence.persistence import PersistenceProvider
from dialogs_framework.persistence.in_memory import InMemoryPersistence
from dialogs_framework.types import dialog, send_message, get_client_response
from dialogs_framework.async_gen_dialogs import run_async_gen_dialog, dialog_result
from dialogs_framework.dialogs import run_dialog

from .test_dialogs import topic_dialog as run_topic_dialog


@dialog(version="1.0")
def fallback_without_client_response():
    yield send_message("Falling back!")


@dialog(version="1.0")
def name_getter_dialog():
    yield send_message("Hello.")
    yield send_message("Nice to meet you!")
    yield send_message("what is your name?")
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def topic_dialog():
    name = yield name_getter_dialog()
    yield send_message(f"Hi {name}!")
    yield send_message("What would you like to talk about")
    topic = yield get_client_response()
    return name, topic


@dialog(version="1.1")
def name_getter_dialog_take_2():
    yield send_message("Tell me your name! Now!!!")
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def fallback_with_client_response():
    yield send_message("Falling back!")
    yield get_client_response()
    yield send_message("Get up fool")


@dialog(version="1.0")
def versioned_subdialog():
    yield send_message("I am a dialog")
    result = yield get_client_response()
    return result


@dialog(version="1.1")
def versioned_subdialog_take_2():
    yield send_message("I have a different version, HA! HA! HA!")
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def dialog_with_subdialog():
    yield versioned_subdialog()
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def dialog_with_subdialog_take_2():
    yield versioned_subdialog_take_2()
    result = yield get_client_response()
    return result


@dialog(version="1.0")
def name_getter_dialog_take_3():
    yield send_message("I need to know your name")
    name = yield get_client_response()
    yield send_message("Wait! i have another message for you!")
    return name


@dialog(version="test")
def echo_dialog(message: str):
    # Release thread
    sleep(0.0001)
    yield send_message(message)


async def run_echo_dialog_task(message: str):
    persistence: PersistenceProvider = InMemoryPersistence()
    test_dialog = echo_dialog(message)
    next_step = await run_async_gen_dialog(test_dialog, persistence, "test")  # type: ignore

    assert len(next_step.messages) == 1

    return next_step.messages[0]


@dialog(version="1.0")
def no_yield_dialog():
    return "hello!"


@dialog(version="1.0")
def dialog_with_no_yield_subdialog():
    next_message = yield no_yield_dialog()
    yield send_message(next_message)
    result = yield get_client_response()
    return result


@dialog(version="1.0")
async def dialog_with_async():
    yield send_message("I need to know your name")
    await asyncio.sleep(0.01)
    name = yield get_client_response()
    yield send_message("Wait! i have another message for you!")

    # can't do that [async gens don't support return value]
    # return name

    # so instead do that
    yield dialog_result(name)


@dialog(version="1.0")
def sub_dialog_with_async():
    name = yield dialog_with_async()
    yield send_message(f"Your name is {name}")
    return name


@dialog(version="1.0")
async def async_dialog_yield_no_await():
    yield send_message("I need to know your name")
    name = yield get_client_response()
    yield send_message(f"Hello {name}!")


@dialog(version="1.0")
async def async_dialog_await_no_yield():
    await asyncio.sleep(0.01)
    return "done"


@dialog(version="1.0")
async def async_dialog_no_await_no_yield():
    return "done"


@dialog(version="1.0")
async def async_dialog_no_result():
    yield send_message("I need to know your name")
    await asyncio.sleep(0.01)
    name = yield get_client_response()
    yield send_message("Wait! i have another message for you!")


@pytest.mark.asyncio
async def test_run_dialog_happy_flow():
    persistence = InMemoryPersistence()

    step1 = await run_async_gen_dialog(name_getter_dialog(), persistence, "")
    assert not step1.is_done
    assert len(step1.messages) == 3

    step2 = await run_async_gen_dialog(name_getter_dialog(), persistence, "Johnny")
    assert step2.is_done
    assert step2.return_value == "Johnny"


@pytest.mark.asyncio
async def test_run_dialog_with_subdialog_happy_flow():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(topic_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = await run_async_gen_dialog(topic_dialog(), persistence, "Johnny")
    assert len(step2.messages) == 2
    assert step2.messages[0] == "Hi Johnny!"

    step3 = await run_async_gen_dialog(topic_dialog(), persistence, "Peanuts")
    assert step3.is_done
    assert step3.return_value == ("Johnny", "Peanuts")


@pytest.mark.asyncio
async def test_run_dialog_raise_exception_changed_version():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(name_getter_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = await run_async_gen_dialog(name_getter_dialog_take_2(), persistence, "Johnny")
    assert step2.messages == ["Tell me your name! Now!!!"]
    assert not step2.is_done


@pytest.mark.asyncio
async def test_run_dialog_with_fallback_without_client_response():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(
        name_getter_dialog(), persistence, "", fallback_without_client_response()
    )
    assert step1.messages == ["Hello.", "Nice to meet you!", "what is your name?"]

    step2 = await run_async_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    assert step2.messages == ["Falling back!", "Tell me your name! Now!!!"]

    step3 = await run_async_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Johnny", fallback_without_client_response()
    )
    assert step3.is_done
    assert step3.return_value == "Johnny"


@pytest.mark.asyncio
async def test_run_dialog_with_fallback_with_client_response():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(
        name_getter_dialog(), persistence, "", fallback_with_client_response()
    )
    assert len(step1.messages) == 3

    step2 = await run_async_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Juanito", fallback_with_client_response()
    )
    assert step2.messages == ["Falling back!"]
    # We don't test for the return value of this part because we don't handle the internal fallback dialogs_framework return_value

    step3 = await run_async_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_with_client_response()
    )
    assert step3.messages == ["Get up fool", "Tell me your name! Now!!!"]

    step4 = await run_async_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Johnny", fallback_with_client_response()
    )
    assert step4.is_done
    assert step4.return_value == "Johnny"


@pytest.mark.asyncio
async def test_run_dialog_with_fallback_on_subdialog_version_mismatch():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(
        dialog_with_subdialog(), persistence, "", fallback_without_client_response()
    )
    assert step1.messages == ["I am a dialog"]

    step2 = await run_async_gen_dialog(
        dialog_with_subdialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    assert step2.messages == ["Falling back!", "I have a different version, HA! HA! HA!"]


@pytest.mark.asyncio
async def test_run_dialog_with_fallback_truncates_leftover_messages():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(
        name_getter_dialog_take_3(), persistence, "", fallback_with_client_response()
    )
    assert step1.messages == ["I need to know your name"]

    step2 = await run_async_gen_dialog(
        name_getter_dialog_take_2(), persistence, "Julia", fallback_without_client_response()
    )
    # We expect the second message of `name_getter_dialog_take_3` not to be here
    assert step2.messages == ["Falling back!", "Tell me your name! Now!!!"]


@pytest.mark.asyncio
async def test_run_dialog_returns_leftover_messages_when_done():
    persistence = InMemoryPersistence()
    next_step = await run_async_gen_dialog(send_message("what is your name?"), persistence, "")

    assert next_step.is_done
    assert next_step.messages == ["what is your name?"]


@pytest.mark.asyncio
async def test_running_dialogs_concurrently_handles_messages_apart():
    messages = ["first", "second", "third"]

    results = await asyncio.gather(*[run_echo_dialog_task(message) for message in messages])

    assert results == messages


@pytest.mark.asyncio
async def test_dialog_with_no_steps():
    persistence = InMemoryPersistence()

    next_step = await run_async_gen_dialog(no_yield_dialog(), persistence, "")
    assert next_step.is_done
    assert next_step.return_value == "hello!"


@pytest.mark.asyncio
async def test_dialog_with_no_steps_as_subdialog():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(dialog_with_no_yield_subdialog(), persistence, "")
    assert step1.messages == ["hello!"]
    assert not step1.is_done

    step2 = await run_async_gen_dialog(dialog_with_no_yield_subdialog(), persistence, "Julia")
    assert step2.is_done
    assert step2.return_value == "Julia"


@pytest.mark.asyncio
async def test_run_dialog_with_gen_dialog():
    persistence = InMemoryPersistence()
    step1 = run_dialog(run_topic_dialog(), persistence, "")
    assert len(step1.messages) == 3

    step2 = await run_async_gen_dialog(topic_dialog(), persistence, "Johnny")
    assert len(step2.messages) == 2
    assert step2.messages[0] == "Hi Johnny!"

    step3 = await run_async_gen_dialog(topic_dialog(), persistence, "Peanuts")
    assert step3.is_done
    assert step3.return_value == ("Johnny", "Peanuts")


@pytest.mark.asyncio
async def test_dialog_with_async():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(dialog_with_async(), persistence, "")
    assert len(step1.messages) == 1

    step2 = await run_async_gen_dialog(dialog_with_async(), persistence, "Johnny")
    assert len(step2.messages) == 1
    assert step2.is_done
    assert step2.return_value == ("Johnny")


@pytest.mark.asyncio
async def test_subdialog_with_async():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(sub_dialog_with_async(), persistence, "")
    assert len(step1.messages) == 1

    step2 = await run_async_gen_dialog(sub_dialog_with_async(), persistence, "Johnny")
    assert len(step2.messages) == 2
    assert step2.messages[1] == "Your name is Johnny"
    assert step2.is_done
    assert step2.return_value == ("Johnny")


@pytest.mark.asyncio
async def test_async_dialog_no_await_yes_yield():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(async_dialog_yield_no_await(), persistence, "")
    assert len(step1.messages) == 1

    step2 = await run_async_gen_dialog(async_dialog_yield_no_await(), persistence, "Johnny")
    assert len(step2.messages) == 1
    assert step2.messages[0] == "Hello Johnny!"
    assert step2.is_done


@pytest.mark.asyncio
async def test_async_dialog_yes_await_no_yield():
    persistence = InMemoryPersistence()
    step1 = await run_async_gen_dialog(async_dialog_await_no_yield(), persistence, "")
    assert step1.is_done
    assert step1.return_value == "done"
