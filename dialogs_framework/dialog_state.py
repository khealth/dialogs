from typing import List, TypeVar, Generic, Optional
from dataclasses import dataclass, field

from .types import BaseDialog, DialogStateException


T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    return_value: T


@dataclass
class DialogState(Generic[T]):
    """
    This class represents the state of a dialog. It contains the information
    that must be persisted to continue the dialog where it left off.

    It can be initialized directly by providing the version, name attributes,
    or using the factory method new_empty_state.
    """

    version: str
    name: str
    subdialogs: List["DialogState"] = field(default_factory=list)
    result: Optional[Result] = None
    sent_to_client: bool = False
    handling_fallback: bool = False

    def get_subdialog_state(self, subdialog_index: int, subdialog: BaseDialog[T]) -> "DialogState":
        if len(self.subdialogs) == subdialog_index:
            self.subdialogs.append(new_empty_state(subdialog))

        subdialog_state = self.subdialogs[subdialog_index]
        return subdialog_state

    @property
    def return_value(self) -> T:
        if not self.result:
            raise DialogStateException("Dialog not done yet")

        return self.result.return_value

    @return_value.setter
    def return_value(self, value: T) -> None:
        if self.result:
            raise DialogStateException("Dialog is done, cannot set return value")

        self.result = Result(value)

    @property
    def is_done(self) -> bool:
        return self.result is not None

    def reset(self, dialog: BaseDialog, fallback_mode: bool) -> None:
        self.subdialogs = []
        self.version = dialog.version
        self.name = dialog.name
        self.result = None
        self.sent_to_client = False
        self.handling_fallback = fallback_mode


def new_empty_state(dialog: BaseDialog[T]) -> DialogState[T]:
    return DialogState(version=dialog.version, name=dialog.name)


def state_from_dict(raw_state: dict) -> DialogState:
    return DialogState(
        version=raw_state["version"],
        name=raw_state["name"],
        result=None if raw_state["result"] is None else Result(raw_state["result"]["return_value"]),
        sent_to_client=raw_state["sent_to_client"],
        subdialogs=[
            state_from_dict(raw_subdialog_state) for raw_subdialog_state in raw_state["subdialogs"]
        ],
    )
