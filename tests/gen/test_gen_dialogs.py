from typing import Tuple


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
    topic: str = yield get_client_response()
    return name, topic

@dialog(version="1.1")
def name_getter_dialog_take_2() -> str:
    yield send_message("Tell me your name! Now!!!")
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
    step1 = run_gen_dialog(name_getter_dialog(), persistence, "", fallback_without_client_response())
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