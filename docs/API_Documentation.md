# API Documentation

## Table of Contents

- [examples](#category-examples)
  - [api](#path-api)
- [Data Models](#data-models)
  - [Item](#model-item)

---

## Category: examples <a id="category-examples"></a>

### Path: api <a id="path-api"></a>

#### GET /api/items/

**Function:** `read_items`

**Source File:** `routers\router.py`

**Tags:** `examples`

**Description:**

Retrieve a list of items.  - `q`: Optional query parameter to filter items by name.

**Response Model:** `List`

**Example Request:**

```python
import requests

url = 'https://localhost:8001/api/items/'

response = requests.get(url)
print(response.status_code)
print(response.json())
```

**Example Response:**

```json
{
    // List structure
}
```

---

#### POST /api/items/

**Function:** `create_item`

**Source File:** `routers\router.py`

**Tags:** `examples`

**Description:**

Create a new item.  - `item`: The item to create.

**Request Body:** [`Item`](#model-item)

**Response Model:** [`Item`](#model-item)

**Example Request:**

```python
import requests

url = 'https://localhost:8001/api/items/'

# Request payload
payload = {
    'name': 'example',
    'description': 'example',
    'price': 1.0,
    'tax': 1.0,
}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())
```

---

#### GET /api/items/{item_id}

**Function:** `read_item`

**Source File:** `routers\router.py`

**Tags:** `examples`

**Description:**

Retrieve an item by its ID.  - `item_id`: The ID of the item to retrieve.

**Response Model:** [`Item`](#model-item)

**Example Request:**

```python
import requests

# Path parameters
item_id = 'value'  # Replace with actual item_id

url = 'https://localhost:8001/' + 'api' + '/' + 'items' + '/' + item_id

response = requests.get(url)
print(response.status_code)
print(response.json())
```

**Example Response:**

```json
{
  "name": "example",
  "description": "example",
  "price": 1.0,
  "tax": 1.0
}
```

---

#### PUT /api/items/{item_id}

**Function:** `update_item`

**Source File:** `routers\router.py`

**Tags:** `examples`

**Description:**

Update an item by its ID.  - `item_id`: The ID of the item to update. - `item`: The updated item data.

**Request Body:** [`Item`](#model-item)

**Response Model:** [`Item`](#model-item)

**Example Request:**

```python
import requests

# Path parameters
item_id = 'value'  # Replace with actual item_id

url = 'https://localhost:8001/' + 'api' + '/' + 'items' + '/' + item_id

# Request payload
payload = {
    'name': 'example',
    'description': 'example',
    'price': 1.0,
    'tax': 1.0,
}

response = requests.put(url, json=payload)
print(response.status_code)
print(response.json())
```

---

#### DELETE /api/items/{item_id}

**Function:** `delete_item`

**Source File:** `routers\router.py`

**Tags:** `examples`

**Description:**

Delete an item by its ID.  - `item_id`: The ID of the item to delete.

**Example Request:**

```python
import requests

# Path parameters
item_id = 'value'  # Replace with actual item_id

url = 'https://localhost:8001/' + 'api' + '/' + 'items' + '/' + item_id

response = requests.delete(url)
print(response.status_code)
print(response.json())
```

---

## Data Models {#data-models}

### Item <a id="model-item"></a>

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | `Optional[str]` | No |  (default: `None`) |
| `name` | `str` | Yes |  |
| `price` | `float` | Yes |  |
| `tax` | `Optional[float]` | No |  (default: `None`) |

**Example:**

```python
from pydantic import BaseModel

class Item(BaseModel):
    description: Optional[str] = None
    name: str
    price: float
    tax: Optional[float] = None
```

```json
{
  "name": "example",
  "price": 1.0
}
```

---

