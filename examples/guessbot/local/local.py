from random import randrange


def guess_game():
    print("Guess a number between 1 and 10.")
    correct_number = randrange(1, 11)

    while True:
        guess = input()
        if int(guess) == correct_number:
            break
        print("That's not it...")

    print("Awesome! The number is ", correct_number)
    print("Bye bye.")


guess_game()
