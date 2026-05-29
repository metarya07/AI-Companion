from memory.database import initialize_database
from skills.memory_skill import remember, recall

initialize_database()

print(remember("Buy milk"))
print(remember("Finish OS assignment"))

print()
print(recall())
