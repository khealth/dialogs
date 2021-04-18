from dataclasses import dataclass
import random

from dialogs import run_dialog, run, InMemoryPersistence, dialog

from .primitives import send_message, prompt, chain, multichoice, yes_no

DRAGON_DIALOG = chain(
    [
        prompt("Do you like dragons?"),
        prompt("Seriously, do you like dragons?"),
        send_message("Good, because we REALLY Like dragons here."),
        yes_no("Wanna hear more?", "Are you sure?"),
    ]
)
COVID_DIALOG = chain(
    [
        prompt("How scary is covid?"),
        prompt("Seriously, are you scared?"),
        send_message("I thought so."),
        prompt("You're just playing though, right?"),
    ]
)


@dialog(version="1.0")
def intelligent_dialog():
    name = run(prompt("Hey! What's your name?"))
    random_animal = random.choice(["turtle", "pokemon", "hummingbird", "caterpillar"])
    run(
        chain(
            [
                send_message("What a beautiful name!"),
                send_message(f"I had a {random_animal} called {name} once."),
                send_message(f"So, {name}, if that's your real name..."),
            ]
        )
    )

    interested = run(
        yes_no("Would you like to talk to me today?", "A simple yes or no would be good.")
    )
    if not interested:
        return

    choice = run(
        multichoice(
            f"What would you like to talk about?",
            f"Come on {name}! Now you know that's not valid. What will it be?",
            ["Dragons", "COVID"],
        )
    )

    if choice == 0:
        run(DRAGON_DIALOG)
    else:
        run(COVID_DIALOG)


@dataclass
class ChatServer:
    persistence = InMemoryPersistence[str]()

    def get_server_messages(self, client_response):
        main_dialog = intelligent_dialog()

        dialog_step = run_dialog(main_dialog, self.persistence, client_response)
        if not dialog_step.is_done:
            return dialog_step.messages
        return_value = dialog_step.return_value

        return [f"Dialog is done, return value is: {return_value}", "Ciao!"]
