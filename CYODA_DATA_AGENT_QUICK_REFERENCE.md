# Cyoda Data Agent - Quick Reference

## Setup
```
Host: https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org
Client ID: F7NN4O
Client Secret: KyTcXdJL4QVDS9T1dQoQ
```

---

## 1️⃣ CREATE - Add a new entity

**Prompt**: "Create a new cat with name Whiskers, age 3, color orange, breed tabby, vaccinated true"

**What it does**: Saves a new entity to your environment and returns its ID

**Response**: 
```
✓ Created cat: Whiskers
  ID: dfa0abc4-336e-11b2-b029-3e29a98ff4a3
```

---

## 2️⃣ GET - Retrieve a single entity

**Prompt**: "Get the cat with ID dfa0abc4-336e-11b2-b029-3e29a98ff4a3"

**What it does**: Fetches a specific entity by its technical UUID

**Response**:
```
✓ Retrieved cat: Whiskers
  Age: 3, Color: orange, Breed: tabby
```

---

## 3️⃣ FIND ALL - List all entities of a type

**Prompt**: "Show me all cats in my environment"

**What it does**: Retrieves every entity of the specified type

**Response**:
```
✓ Found 10 total cats
  1. Mochi
  2. Whiskers
  3. Luna
  ... and 7 more
```

---

## 4️⃣ SEARCH - Find entities by condition

**Prompt**: "Find all cats where color is orange"

**What it does**: Searches for entities matching the specified field values

**Response**:
```
✓ Found 2 orange cats
  1. Whiskers
  2. Bella
```

---

## Multi-Field Search

**Prompt**: "Search for cats where color is white and breed is Persian"

**What it does**: Finds entities matching ALL conditions (AND logic)

**Response**:
```
✓ Found 1 matching cat
  1. Luna (white, Persian)
```

---

## Common Entity Types

- `cat` - Pet cats
- `product` - Products/items
- `user` - User accounts
- `order` - Orders
- `customer` - Customers
- *(any custom entity in your environment)*

---

## Tips

💡 **For CREATE**: Provide all required fields for your entity model  
💡 **For GET**: You need the exact technical UUID  
💡 **For FIND ALL**: Use when you want to see everything (can be slow for large datasets)  
💡 **For SEARCH**: Use for filtering by specific field values  

---

## Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| Unauthorized | Invalid credentials | Check client_id and client_secret |
| Entity not found | Wrong ID or entity doesn't exist | Verify the entity ID |
| Invalid entity model | Entity type doesn't exist | Check entity model name |
| Missing required fields | Entity data incomplete | Provide all required fields |

