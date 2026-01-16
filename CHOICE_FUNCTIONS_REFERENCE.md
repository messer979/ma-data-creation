# Quick Reference: choiceOrder vs choiceUnique

## choiceOrder
**Sequential selection** - Values are selected in order from first to last, then resets.

```json
"RandomFields": [
  {
    "FieldName": "Status",
    "FieldType": "choiceOrder(PENDING,ACTIVE,COMPLETE)"
  }
]
```

**Output for 7 records:**
1. PENDING
2. ACTIVE
3. COMPLETE
4. PENDING
5. ACTIVE
6. COMPLETE
7. PENDING

---

## choiceUnique
**Random non-repeating** - Values are selected randomly without repetition until all are used, then resets.

```json
"RandomFields": [
  {
    "FieldName": "Status",
    "FieldType": "choiceUnique(PENDING,ACTIVE,COMPLETE)"
  }
]
```

**Output for 7 records (example):**
1. ACTIVE
2. COMPLETE
3. PENDING
4. ACTIVE
5. PENDING
6. COMPLETE
7. PENDING

---

## choice
**Random with repetition** - Values are selected randomly with possible immediate repetition.

```json
"RandomFields": [
  {
    "FieldName": "Status",
    "FieldType": "choice(PENDING,ACTIVE,COMPLETE)"
  }
]
```

**Output for 7 records (example):**
1. ACTIVE
2. ACTIVE
3. PENDING
4. COMPLETE
5. ACTIVE
6. PENDING
7. PENDING

---

## When to Use What

| Scenario | Use This |
|----------|----------|
| Need predictable repeating pattern | `choiceOrder` |
| Need even distribution across records | `choiceOrder` |
| Testing with known sequences | `choiceOrder` |
| Want variety without immediate repeats | `choiceUnique` |
| Need random but fair distribution | `choiceUnique` |
| Don't care about order or uniqueness | `choice` |
| Need completely random data | `choice` |
