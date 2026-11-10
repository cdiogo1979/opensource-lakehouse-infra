-- Basic access
SELECT * FROM lake.warehouse.demo.customers;
SELECT * FROM lake.warehouse.demo.products;
SELECT * FROM lake.warehouse.demo.orders;

-- Revenue by category
SELECT
    p.category,
    SUM(o.quantity * o.unit_price) AS revenue,
    COUNT(*) AS order_lines
FROM lake.warehouse.demo.orders o
JOIN lake.warehouse.demo.products p
  ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- Revenue by country
SELECT
    c.country,
    SUM(o.quantity * o.unit_price) AS revenue
FROM lake.warehouse.demo.orders o
JOIN lake.warehouse.demo.customers c
  ON o.customer_id = c.customer_id
GROUP BY c.country
ORDER BY revenue DESC;

-- Semantic view
CREATE VIEW lake.warehouse.demo.order_summary AS
SELECT
    o.order_id,
    o.order_date,
    c.customer_name,
    c.country,
    c.segment,
    p.product_name,
    p.category,
    o.quantity,
    o.unit_price,
    o.quantity * o.unit_price AS line_revenue
FROM lake.warehouse.demo.orders o
JOIN lake.warehouse.demo.customers c
  ON o.customer_id = c.customer_id
JOIN lake.warehouse.demo.products p
  ON o.product_id = p.product_id;

-- Query the view
SELECT
    category,
    country,
    SUM(line_revenue) AS revenue
FROM lake.warehouse.demo.order_summary
GROUP BY category, country
ORDER BY revenue DESC;
