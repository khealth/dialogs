from ..dialogs.message_queue import MessageQueue


def test_happy_flow():
    messages = ["1", "2", "3"]

    queue = MessageQueue()
    for message in messages:
        queue.enqueue(message)

    assert queue.dequeue_all() == ["1", "2", "3"]
    assert queue.dequeue_all() == []
