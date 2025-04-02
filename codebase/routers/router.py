from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["examples"])

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

@router.get("/items/", response_model=List[Item])
async def read_items(q: Optional[str] = Query(None, max_length=50)):
    """
    Retrieve a list of items.
    
    - `q`: Optional query parameter to filter items by name.
    """
    items = [
        {"name": "Foo", "description": "The Foo Wrestlers", "price": 50.2, "tax": 2.5},
        {"name": "Bar", "description": "The Bar Fighters", "price": 62, "tax": 3.1},
        {"name": "Baz", "description": "The Baz Destroyers", "price": 50.2, "tax": 2.5}
    ]
    
    if q:
        filtered_items = [item for item in items if q.lower() in item["name"].lower()]
        return filtered_items
    
    return items

@router.post("/items/", response_model=Item, status_code=201)
async def create_item(item: Item):
    """
    Create a new item.
    
    - `item`: The item to create.
    """
    return item

@router.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int):
    """
    Retrieve an item by its ID.
    
    - `item_id`: The ID of the item to retrieve.
    """
    if item_id > 1000:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"name": f"Item {item_id}", "description": "Example Item", "price": 10.5, "tax": 0.5}

@router.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    """
    Update an item by its ID.
    
    - `item_id`: The ID of the item to update.
    - `item`: The updated item data.
    """
    return item

@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    """
    Delete an item by its ID.
    
    - `item_id`: The ID of the item to delete.
    """
    return None
