CREATE OR REPLACE FORCE NONEDITIONABLE VIEW "OMA"."CUSTOMER_ORDER_PRODUCTS" ("
ORDER_ID", "ORDER_TMS", "ORDER_STATUS", "CUSTOMER_ID", "EMAIL_ADDRESS", "FULL_NA
ME", "ORDER_TOTAL", "ITEMS") AS
  SELECT o.order_id, o.order_tms, o.order_status,
	 c.customer_id, c.email_address, c.full_name,
	 SUM ( oi.quantity * oi.unit_price ) order_total,
	 LISTAGG (
	   p.product_name, ', '
	   ON OVERFLOW TRUNCATE '...' WITH COUNT
	 ) WITHIN GROUP ( ORDER BY oi.line_item_id ) items
  FROM	 orders o
  JOIN	 order_items oi
  ON	 o.order_id = oi.order_id
  JOIN	 customers c
  ON	 o.customer_id = c.customer_id
  JOIN	 products p
  ON	 oi.product_id = p.product_id
  GROUP  BY o.order_id, o.order_tms, o.order_status,
	 c.customer_id, c.email_address, c.full_name;