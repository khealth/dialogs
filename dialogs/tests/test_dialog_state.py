import pytest

from ..dialogs.types import get_client_response, send_message, dialog
from ..dialogs.dialog_state import new_empty_state, DialogStateException, state_from_dict
from ..dialogs.dialogs import run


@dialog(version="1.0")
def fun_dialog():
    run(send_message("Hi there."))
    run(send_message("How are you?"))
    return run(get_client_response())


def test_state_from_dict_no_subdialogs_result_none():
    raw = {
        "version": "1.0",
        "name": "fun_dialog",
        "result": None,
        "subdialogs": [],
        "sent_to_client": False,
    }

    state = state_from_dict(raw)

    assert state.version == "1.0"
    assert state.name == "fun_dialog"
    assert not state.is_done
    assert state.subdialogs == []
    assert not state.sent_to_client


def test_state_from_dict_no_subdialogs_result_full():
    raw = {
        "version": "1.0",
        "name": "fun_dialog",
        "result": {"return_value": 6},
        "subdialogs": [],
        "sent_to_client": False,
    }

    state = state_from_dict(raw)

    assert state.version == "1.0"
    assert state.name == "fun_dialog"
    assert state.is_done
    assert state.return_value == 6
    assert state.subdialogs == []
    assert not state.sent_to_client


def test_state_from_dict_nested_state():
    raw_subdialog = {
        "version": "1.0",
        "name": "fun_subdialog",
        "result": {"return_value": 6},
        "subdialogs": [],
        "sent_to_client": False,
    }
    raw = {
        "version": "1.0",
        "name": "fun_dialog",
        "result": None,
        "subdialogs": [raw_subdialog],
        "sent_to_client": False,
    }

    state = state_from_dict(raw)

    assert len(state.subdialogs) == 1
    assert state.subdialogs[0].version == "1.0"
    assert state.subdialogs[0].name == "fun_subdialog"
    assert state.subdialogs[0].is_done
    assert state.subdialogs[0].return_value == 6
    assert state.subdialogs[0].subdialogs == []
    assert not state.subdialogs[0].sent_to_client


def test_new_empty_state_correct_for_get_client_response():
    state = new_empty_state(get_client_response())

    assert state.subdialogs == []
    assert not state.is_done
    assert state.version == "1.0"
    assert state.name == "get_client_response"
    assert not state.sent_to_client


def test_new_empty_state_correct_for_send_message():
    state = new_empty_state(send_message("some message"))

    assert state.subdialogs == []
    assert not state.is_done
    assert state.version == "1.0"
    assert state.name == "send_message"
    assert not state.sent_to_client


def test_new_empty_state_correct_for_dialog():
    state = new_empty_state(fun_dialog())

    assert state.subdialogs == []
    assert not state.is_done
    assert state.version == "1.0"
    assert state.name == "fun_dialog"
    assert not state.sent_to_client


def test_get_subdialog_state_new_state_case():
    state = new_empty_state(fun_dialog())
    subdialog_state = state.get_subdialog_state(0, send_message("Hi!"))

    assert not subdialog_state.is_done


def test_get_subdialog_state_refetch_existing_subdialog_state():
    state = new_empty_state(fun_dialog())
    subdialog_state = state.get_subdialog_state(0, send_message("Hi!"))
    subdialog_state.return_value = 6

    # Now fetch the state again, and see that the return value is retained
    subdialog_state_second_fetch = state.get_subdialog_state(0, send_message("Hi!"))
    assert subdialog_state_second_fetch.is_done
    assert subdialog_state_second_fetch.return_value == 6


def test_set_return_value_sets_is_done():
    state = new_empty_state(fun_dialog())

    state.return_value = 6

    assert state.return_value == 6
    assert state.is_done


def test_set_return_value_twice_raises_exception():
    state = new_empty_state(fun_dialog())
    state.return_value = 6

    with pytest.raises(DialogStateException):
        state.return_value = 7


def test_get_return_value_before_set_raises_exception():
    state = new_empty_state(fun_dialog())

    with pytest.raises(DialogStateException):
        _ = state.return_value


def test_version_property():
    @dialog(version="123")
    def some_dialog():
        pass

    state = new_empty_state(some_dialog())

    assert state.version == "123"
