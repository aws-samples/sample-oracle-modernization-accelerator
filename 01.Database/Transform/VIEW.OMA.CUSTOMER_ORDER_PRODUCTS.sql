CREATE OR REPLACE VIEW oma.customer_order_products (
  order_id, order_tms, order_status, customer_id,
  email_address, full_name, order_total, items
) AS
SELECT 
   o.order_id, 
   o.order_tms, 
   o.order_status,
   c.customer_id, 
   c.email_address, 
   c.full_name,
   SUM(oi.quantity * oi.unit_price) AS order_total,
   STRING_AGG(p.product_name, ', ' ORDER BY oi.line_item_id) AS items
FROM 
   orders o
JOIN 
   order_items oi ON o.order_id = oi.order_id
JOIN 
   customers c ON o.customer_id = c.customer_id
JOIN 
   products p ON oi.product_id = p.product_id
GROUP BY 
   o.order_id, o.order_tms, o.order_status,
   c.customer_id, c.email_address, c.full_name;
