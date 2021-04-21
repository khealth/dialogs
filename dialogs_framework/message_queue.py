from dataclasses import dataclass, field
from typing import List, Generic, TypeVar

ServerMessage = TypeVar("ServerMessage")


@dataclass
class MessageQueue(Generic[ServerMessage]):
    """
    This is an in-memory queue.

    It is used to accumulate all server messages until the next get_client_response
    call, which flushes it.
    """

    _queue: List[ServerMessage] = field(default_factory=list)

    def enqueue(self, message: ServerMessage) -> None:
        """
        Add a message to the queue.
        """
        self._queue.append(message)

    def dequeue_all(self) -> List[ServerMessage]:
        """
        Remove all messages from the queue and return them.
        """
        messages = self._queue
        self._queue = []
        return messages
