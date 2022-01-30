import sys
from .chat_server import ChatServer


def get_response_from_stdin():
    return sys.stdin.readline()


def main():
    chat_server = ChatServer()
    client_response = ""
    server_message = ""
    while not server_message.lower().startswith("ciao"):
        for server_message in chat_server.get_server_messages(client_response):
            print("Server:", server_message)
        client_response = get_response_from_stdin().strip()


if __name__ == "__main__":
    main()
