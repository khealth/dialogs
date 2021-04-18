from requests import post
import uuid

URL = "http://localhost:8000/"


def play():
    id = str(uuid.uuid4())
    while True:
        responses = post(URL, params={"message": input(), "chat_id": id}).json()
        for response in responses:
            print(response)


play()
