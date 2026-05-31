from memory.database import save_memory, get_memories, delete_memory


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


def forget(memory_id):
    deleted_rows = delete_memory(memory_id)

    if deleted_rows:
        return f"Memory {memory_id} deleted."

    return f"Memory {memory_id} not found."
