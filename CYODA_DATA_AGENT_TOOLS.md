# Cyoda Data Agent - Available Tools

## Overview
The Cyoda Data Agent provides 4 core tools for interacting with your Cyoda environment using your own credentials.

---

## Tool 1: CREATE ENTITY
**Function**: `create_entity()`

Creates a new entity in your Cyoda environment.

### Parameters
- `client_id` (string): Your OAuth client ID
- `client_secret` (string): Your OAuth client secret
- `cyoda_host` (string): Your Cyoda environment URL
- `entity_model` (string): Entity type (e.g., "cat", "product", "user")
- `entity_data` (object): Entity fields and values

### Example
```python
await create_entity(
    client_id="F7NN4O",
    client_secret="KyTcXdJL4QVDS9T1dQoQ",
    cyoda_host="https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org",
    entity_model="cat",
    entity_data={
        "name": "Whiskers",
        "age": 3,
        "color": "orange",
        "breed": "tabby",
        "vaccinated": True
    }
)
```

### Returns
- `success` (boolean): Operation status
- `data` (object): Created entity with technical_id

---

## Tool 2: GET ENTITY
**Function**: `get_entity()`

Retrieves a single entity by its technical ID.

### Parameters
- `client_id` (string): Your OAuth client ID
- `client_secret` (string): Your OAuth client secret
- `cyoda_host` (string): Your Cyoda environment URL
- `entity_model` (string): Entity type
- `entity_id` (string): Technical UUID of the entity

### Example
```python
await get_entity(
    client_id="F7NN4O",
    client_secret="KyTcXdJL4QVDS9T1dQoQ",
    cyoda_host="https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org",
    entity_model="cat",
    entity_id="0d15be2e-336e-11b2-b029-3e29a98ff4a3"
)
```

### Returns
- `success` (boolean): Operation status
- `data` (object): Entity details

---

## Tool 3: FIND ALL ENTITIES
**Function**: `find_all_entities()`

Retrieves all entities of a specific type.

### Parameters
- `client_id` (string): Your OAuth client ID
- `client_secret` (string): Your OAuth client secret
- `cyoda_host` (string): Your Cyoda environment URL
- `entity_model` (string): Entity type

### Example
```python
await find_all_entities(
    client_id="F7NN4O",
    client_secret="KyTcXdJL4QVDS9T1dQoQ",
    cyoda_host="https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org",
    entity_model="cat"
)
```

### Returns
- `success` (boolean): Operation status
- `data` (array): List of all entities

---

## Tool 4: SEARCH ENTITIES
**Function**: `search_entities()`

Searches entities by field conditions (equality-based).

### Parameters
- `client_id` (string): Your OAuth client ID
- `client_secret` (string): Your OAuth client secret
- `cyoda_host` (string): Your Cyoda environment URL
- `entity_model` (string): Entity type
- `search_conditions` (object): Field-value pairs to match

### Example
```python
await search_entities(
    client_id="F7NN4O",
    client_secret="KyTcXdJL4QVDS9T1dQoQ",
    cyoda_host="https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org",
    entity_model="cat",
    search_conditions={"color": "orange", "breed": "tabby"}
)
```

### Returns
- `success` (boolean): Operation status
- `data` (array): Matching entities

---

## Key Features

✅ **Multi-tenant**: Use your own credentials for your environment  
✅ **Secure**: OAuth2 authentication with token caching  
✅ **Flexible**: Works with any entity model in your Cyoda environment  
✅ **Reliable**: Automatic error handling and logging  

---

## Error Handling

All tools return a consistent response format:
```json
{
  "success": true/false,
  "data": {...},
  "error": "error message if success=false"
}
```

