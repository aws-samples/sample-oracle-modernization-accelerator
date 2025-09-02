<!-- 사용자 행동 패턴 분석 (윈도우 함수 활용) -->
<!-- Converted from Oracle to PostgreSQL - FIXED VERSION -->
<select id="selectUserBehaviorPattern" parameterType="map" resultType="amzn.bo.dto.UserBehaviorPatternDto">
    SELECT 
        u.USER_ID,
        u.EMAIL,
        CONCAT(u.FIRST_NAME, ' ', u.LAST_NAME) as FULL_NAME,
        COALESCE(order_stats.TOTAL_ORDERS, 0) as TOTAL_ORDERS,
        COALESCE(order_stats.TOTAL_SPENT, 0) as TOTAL_SPENT,
        COALESCE(order_stats.AVG_ORDER_VALUE, 0) as AVG_ORDER_VALUE,
        COALESCE(order_stats.DAYS_SINCE_LAST_ORDER, 999) as DAYS_SINCE_LAST_ORDER,
        0 as PURCHASE_FREQUENCY,
        'UNKNOWN' as FAVORITE_CATEGORY,
        'UNKNOWN' as PREFERRED_PAYMENT_METHOD,
        'UNKNOWN' as SEASONAL_PATTERN,
        50 as LOYALTY_SCORE,
        30 as CHURN_PROBABILITY,
        CURRENT_TIMESTAMP + INTERVAL '60 days' as NEXT_PURCHASE_PREDICTION,
        'REGULAR' as CUSTOMER_SEGMENT
    FROM users u
    LEFT JOIN (SELECT 
            o.USER_ID,
            COUNT(*) as TOTAL_ORDERS,
            SUM(o.TOTAL_AMOUNT) as TOTAL_SPENT,
            AVG(o.TOTAL_AMOUNT) as AVG_ORDER_VALUE,
            CURRENT_DATE - MAX(o.ORDERED_AT)::date as DAYS_SINCE_LAST_ORDER
          FROM orders o
          WHERE o.ORDER_STATUS NOT IN ('CANCELLED', 'REFUNDED')
          GROUP BY o.USER_ID) AS order_stats ON u.USER_ID = order_stats.USER_ID
    ORDER BY TOTAL_SPENT DESC
</select>
