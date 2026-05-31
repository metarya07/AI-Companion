from memory.database import initialize_database
from skills.memory_skill import remember, recall, forget

initialize_database()

print(remember("Buy milk"))
print(remember("Finish OS assignment"))

print()
print("=== BEFORE DELETE ===")
print(recall())

print()
print("=== DELETE MEMORY 1 ===")
print(forget(1))

print()
print("=== AFTER DELETE ===")
print(recall())

print()
print("=== DELETE NON-EXISTENT ===")
print(forget(999))
