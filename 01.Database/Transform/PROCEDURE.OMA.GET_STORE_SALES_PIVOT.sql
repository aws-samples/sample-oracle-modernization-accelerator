CREATE OR REPLACE PROCEDURE get_store_sales_pivot()
LANGUAGE plpgsql
AS $$
DECLARE
   l_sql TEXT;
BEGIN
   l_sql := '
       SELECT 
           store_name,
           SUM(CASE WHEN order_status = ''PENDING'' THEN total_amount ELSE 0 END) AS pending_orders,
           SUM(CASE WHEN order_status = ''PROCESSING'' THEN total_amount ELSE 0 END) AS processing_orders,
           SUM(CASE WHEN order_status = ''SHIPPED'' THEN total_amount ELSE 0 END) AS shipped_orders,
           SUM(CASE WHEN order_status = ''DELIVERED'' THEN total_amount ELSE 0 END) AS delivered_orders
       FROM (
           SELECT 
               s.store_name, 
               o.order_status, 
               SUM(oi.quantity * oi.unit_price) as total_amount
           FROM 
               stores s
           LEFT JOIN 
               orders o ON s.store_id = o.store_id
           LEFT JOIN 
               order_items oi ON o.order_id = oi.order_id
           GROUP BY 
               s.store_name, o.order_status
       ) subquery
       GROUP BY 
           store_name
       ORDER BY 
           store_name';

   EXECUTE l_sql;
END;
$$;
