from core.brain import Brain
from memory.database import initialize_database


def main():

    initialize_database()

    brain = Brain()

    print("=== JARVIS v0.4 ===")

    while True:

        user_input = input("JARVIS > ")

        response = brain.process(user_input)

        print(response)

        if user_input.lower() == "exit":
            break


if __name__ == "__main__":
    main()
