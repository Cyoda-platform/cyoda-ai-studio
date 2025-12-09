# Cyoda Data Agent - Example Prompts

The Cyoda Data Agent allows you to interact with your Cyoda environment using natural language. Here are example prompts for each operation:

## Setup Information
You'll need:
- **Cyoda Host**: Your environment URL (e.g., `https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org`)
- **Client ID**: Your OAuth client ID
- **Client Secret**: Your OAuth client secret

---

## 1. CREATE ENTITY

**Example 1: Create a simple cat**
```
Create a new cat entity in my Cyoda environment with:
- Name: Whiskers
- Age: 3
- Color: orange
- Breed: tabby
- Vaccinated: true
```

**Example 2: Create a product**
```
Add a new product to my Cyoda environment:
- Name: Laptop Pro
- Price: 1299.99
- Category: Electronics
- In Stock: true
- Description: High-performance laptop
```

**Example 3: Create a user**
```
Create a user entity with:
- Email: john@example.com
- First Name: John
- Last Name: Doe
- Role: admin
- Active: true
```

---

## 2. GET SINGLE ENTITY

**Example 1: Get a specific cat**
```
Get the cat with ID: 0d15be2e-336e-11b2-b029-3e29a98ff4a3
```

**Example 2: Get a product**
```
Retrieve the product with technical ID: abc123def456
```

**Example 3: Get a user**
```
Fetch the user entity with ID: user-uuid-here
```

---

## 3. FIND ALL ENTITIES

**Example 1: Get all cats**
```
Show me all cat entities in my environment
```

**Example 2: Get all products**
```
List all products in my Cyoda environment
```

**Example 3: Get all users**
```
Retrieve all user entities
```

---

## 4. SEARCH BY CONDITION

**Example 1: Search by single field**
```
Find all cats where color is black
```

**Example 2: Search by multiple fields**
```
Search for cats with:
- Color: white
- Breed: Persian
```

**Example 3: Search products**
```
Find all products where:
- Category: Electronics
- In Stock: true
```

**Example 4: Search users**
```
Search for users where:
- Role: admin
- Active: true
```

---

## Complete Conversation Example

**User**: "Create a new cat named Luna, age 2, white color, Persian breed, vaccinated"

**Agent**: Creates the cat and returns the entity ID

**User**: "Now find all white cats"

**Agent**: Searches and returns all white cats

**User**: "Get the details of the first cat"

**Agent**: Retrieves the specific cat by ID

**User**: "Show me all cats in my environment"

**Agent**: Lists all cat entities

---

## Natural Language Variations

### CREATE
- "Add a new cat to my environment..."
- "Create a product with..."
- "Save a new user entity..."
- "Insert a new record..."

### GET SINGLE
- "Get the cat with ID..."
- "Retrieve the entity..."
- "Show me the details of..."
- "Fetch the record with ID..."

### FIND ALL
- "Show me all cats"
- "List all products"
- "Get all users"
- "Retrieve all entities of type..."

### SEARCH
- "Find cats where color is..."
- "Search for products with..."
- "Show me users where..."
- "Filter entities by..."

