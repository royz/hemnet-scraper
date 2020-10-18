import json
import re

with open('cache/17744.json') as f:
    data = json.load(f)

results = 0
floors = 0
errors = 0

for item in data.values():
    results += 1
    floor = item.get('floor')
    if floor:
        try:
            print(int(floor))
            floors += 1
        except:
            errors += 1
            print(floor)

print(results)
print(floors)
print(errors)
