from skills.system_skill import SystemSkill

system = SystemSkill()

print("=== CPU ===")
print(system.get_cpu_usage())

print()

print("=== RAM ===")
print(system.get_ram_usage())

print()

print("=== STATUS ===")
print(system.get_status())
