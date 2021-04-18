from dataclasses import dataclass
from typing import Optional, TypeVar, Generic

from .persistence import PersistenceProvider
from ..dialog_state import new_empty_state, DialogState
from ..types import BaseDialog

T = TypeVar("T")


@dataclass
class InMemoryPersistence(PersistenceProvider, Generic[T]):
    state: Optional[DialogState[T]] = None

    def save_state(self, state: DialogState[T]) -> None:
        self.state = state

    def get_state(self, dialog: BaseDialog[T]) -> DialogState[T]:
        return self.state if self.state else new_empty_state(dialog)
