CREATE OR REPLACE NONEDITIONABLE PROCEDURE "OMA"."GET_STORE_SALES_PIVOT" IS
  l_sql VARCHAR2(4000);
BEGIN
  l_sql := '
    SELECT *
    FROM (
      SELECT s.store_name, o.order_status, SUM(oi.quantity * oi.unit_price) as t
otal_amount
      FROM stores s
      LEFT JOIN orders o ON s.store_id = o.store_id
      LEFT JOIN order_items oi ON o.order_id = oi.order_id
      GROUP BY s.store_name, o.order_status
    )
    PIVOT (
      SUM(total_amount)
      FOR order_status IN (
	''PENDING'' AS pending_orders,
	''PROCESSING'' AS processing_orders,
	''SHIPPED'' AS shipped_orders,
	''DELIVERED'' AS delivered_orders
      )
    )
    ORDER BY store_name';

  EXECUTE IMMEDIATE l_sql;
END;
/