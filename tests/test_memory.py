from memory.database import initialize_database, save_memory, get_memories

initialize_database()

save_memory("Buy milk")

print(get_memories())
