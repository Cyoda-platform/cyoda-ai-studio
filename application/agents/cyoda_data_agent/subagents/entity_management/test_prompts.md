# Entity Management Subagent Test Prompts

## Complete Flow: Customer and Order Management

### 1. Create a Customer
```
Create a new Customer entity with the following details:
- name: "John Doe"
- email: "john.doe@example.com"
- phone: "555-0101"
- status: "active"
```

### 2. Create Another Customer
```
Create a new Customer entity with:
- name: "Jane Smith"
- email: "jane.smith@example.com"
- phone: "555-0102"
- status: "active"
```

### 3. Search for Active Customers
```
Search for all Customer entities where status equals "active".
```

### 4. Get Statistics for Customers
```
Get statistics for the Customer model to see how many customers we have.
```

### 5. Update Customer Email
```
Update the Customer "John Doe" to change email from "john.doe@example.com" to "john.newemail@example.com".
```

### 6. Create Products
```
Create three Product entities:
- Product 1: name="Laptop", category="Electronics", price=999.99, stock=10
- Product 2: name="Mouse", category="Electronics", price=29.99, stock=50
- Product 3: name="Desk Chair", category="Furniture", price=199.99, stock=15
```

### 7. Search Products by Category
```
Search for all Product entities where category equals "Electronics".
```

### 8. Create an Order for John Doe
```
Create an Order entity with:
- customer_name: "John Doe"
- product_names: ["Laptop", "Mouse"]
- total_amount: 1029.98
- status: "pending"
```

### 9. Create Another Order for Jane Smith
```
Create an Order entity with:
- customer_name: "Jane Smith"
- product_names: ["Desk Chair"]
- total_amount: 199.99
- status: "pending"
```

### 10. Search Pending Orders
```
Search for all Order entities where status equals "pending".
```

### 11. Get Order Statistics
```
Get statistics for the Order model grouped by status to see how many orders are pending, completed, etc.
```

### 12. Update Order Status
```
Update the Order for John Doe to change status from "pending" to "completed".
```

### 13. Search Orders by Amount
```
Search for all Order entities where total_amount is greater than 500.
```

### 14. Get Statistics by State
```
Get entity statistics for all models grouped by state (DRAFT, VALIDATED, PUBLISHED).
```

### 15. Update Product Stock
```
Update the Laptop product to reduce stock from 10 to 8 (after the order).
```

### 16. Search Low Stock Products
```
Search for all Product entities where stock is less than 20.
```

### 17. Delete Completed Orders (Cleanup)
```
Delete all Order entities where status equals "completed" and created_date is older than 30 days.
```

### 18. Final Customer Count
```
Get statistics for the Customer model to confirm final count.
```

