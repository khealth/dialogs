from abc import abstractmethod

from ..types import BaseDialog
from ..dialog_state import DialogState


class PersistenceProvider:
    """
    This is an interface for persisting the dialog state between
    consecustive calls to get_client_response.

    It should be implemented depending on the storage provider.
    """

    @abstractmethod
    def save_state(self, state: DialogState) -> None:
        pass

    @abstractmethod
    def get_state(self, dialog: BaseDialog) -> DialogState:
        pass
