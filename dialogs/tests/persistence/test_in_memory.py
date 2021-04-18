from ...dialogs.types import dialog
from ...dialogs.persistence.in_memory import InMemoryPersistence
from ...dialogs.dialog_state import new_empty_state, DialogState


@dialog(version="1.0")
def some_dialog():
    return 6


def test_save_state_get_state_happy_flow():
    persistence = InMemoryPersistence()
    persistence.save_state(DialogState(name="fake_dialog", version="6"))

    state = persistence.get_state(some_dialog())

    assert state.name == "fake_dialog"
    assert state.version == "6"
    assert not state.is_done


def test_get_empty_state():
    persistence = InMemoryPersistence()

    assert persistence.get_state(some_dialog()) == new_empty_state(some_dialog())
