from core.brain import Brain


def main():

    brain = Brain()

    print("=== JARVIS v0.1 ===")

    while True:

        user_input = input("JARVIS > ")

        response = brain.process(user_input)

        print(response)

        if user_input.lower() == "exit":
            break


if __name__ == "__main__":
    main()
