from memory.database import save_memory, get_memories


def remember(text):
    save_memory(text)
    return "Memory saved."


def recall():
    memories = get_memories()

    if not memories:
        return "No memories found."

    result = []

    for memory_id, memory_text in memories:
        result.append(f"{memory_id}. {memory_text}")

    return "\n".join(result)
