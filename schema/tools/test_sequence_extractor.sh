#!/bin/bash
# Test script for extract_sequence_usage.py

set -e

echo "======================================================================="
echo "Sequence Extractor 테스트"
echo "======================================================================="

# 테스트 디렉토리 생성
TEST_DIR="/tmp/sequence_test_$$"
mkdir -p "$TEST_DIR"

echo ""
echo "[1] 테스트 파일 생성"

# 테스트 MyBatis XML 1
cat > "$TEST_DIR/UserMapper.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.UserMapper">

    <insert id="insertUser" parameterType="User">
        <selectKey keyProperty="userId" resultType="long" order="BEFORE">
            SELECT SEQ_USER_ID.NEXTVAL FROM DUAL
        </selectKey>
        INSERT INTO TB_USER (
            USER_ID,
            USERNAME,
            EMAIL,
            CREATED_AT
        ) VALUES (
            #{userId},
            #{username},
            #{email},
            SYSDATE
        )
    </insert>

    <insert id="insertUserBatch" parameterType="list">
        INSERT INTO TB_USER (USER_ID, USERNAME, EMAIL)
        SELECT SEQ_USER_ID.NEXTVAL, A.* FROM (
            <foreach collection="list" item="user" separator="UNION ALL">
                SELECT #{user.username}, #{user.email} FROM DUAL
            </foreach>
        ) A
    </insert>

</mapper>
EOF

# 테스트 MyBatis XML 2
cat > "$TEST_DIR/OrderMapper.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.OrderMapper">

    <insert id="createOrder" parameterType="Order">
        <selectKey keyProperty="orderNo" resultType="long" order="BEFORE">
            SELECT SEQ_ORDER_NO.NEXTVAL FROM DUAL
        </selectKey>
        INSERT INTO TB_ORDER (
            ORDER_NO,
            USER_ID,
            TOTAL_AMOUNT,
            ORDER_DATE
        ) VALUES (
            #{orderNo},
            #{userId},
            #{totalAmount},
            SYSDATE
        )
    </insert>

    <insert id="createOrderItem">
        INSERT INTO TB_ORDER_ITEM (
            ITEM_NO,
            ORDER_NO,
            PRODUCT_ID,
            QUANTITY
        ) VALUES (
            SEQ_ORDER_ITEM_NO.NEXTVAL,
            #{orderNo},
            #{productId},
            #{quantity}
        )
    </insert>

</mapper>
EOF

# 테스트 SQL 파일
cat > "$TEST_DIR/create_log.sql" << 'EOF'
-- 로그 테이블 INSERT
INSERT INTO TB_LOG (
    LOG_ID,
    LOG_TYPE,
    MESSAGE,
    CREATED_AT
) VALUES (
    SEQ_LOG_ID.NEXTVAL,
    'INFO',
    'Test message',
    SYSDATE
);
EOF

echo "  ✓ 3개 테스트 파일 생성 ($TEST_DIR)"

echo ""
echo "[2] NEXTVAL 스캔 테스트 (LLM 없이)"

python3 /home/ec2-user/workspace/oracle-migration-agent-kr-main/schema-migration/tools/extract_sequence_usage.py \
    "$TEST_DIR" \
    --output "$TEST_DIR/result_no_llm.csv" \
    --no-llm

echo ""
echo "[3] 결과 파일 확인"

if [ -f "$TEST_DIR/result_no_llm.csv" ]; then
    echo "  ✓ CSV 파일 생성됨"
    echo ""
    echo "  CSV 내용:"
    head -20 "$TEST_DIR/result_no_llm.csv" | sed 's/^/    /'

    # 발견 개수 확인
    COUNT=$(tail -n +2 "$TEST_DIR/result_no_llm.csv" | wc -l)
    echo ""
    echo "  총 발견: $COUNT개 NEXTVAL"
else
    echo "  ✗ CSV 파일 생성 실패"
    exit 1
fi

echo ""
echo "[4] JSON 출력 테스트"

python3 /home/ec2-user/workspace/oracle-migration-agent-kr-main/schema-migration/tools/extract_sequence_usage.py \
    "$TEST_DIR" \
    --output "$TEST_DIR/result_no_llm.json" \
    --format json \
    --no-llm

if [ -f "$TEST_DIR/result_no_llm.json" ]; then
    echo "  ✓ JSON 파일 생성됨"
    echo ""
    echo "  JSON 샘플 (첫 항목):"
    cat "$TEST_DIR/result_no_llm.json" | python3 -m json.tool | head -20 | sed 's/^/    /'
else
    echo "  ✗ JSON 파일 생성 실패"
fi

echo ""
echo "======================================================================="
echo "테스트 완료!"
echo "======================================================================="
echo ""
echo "테스트 파일 위치: $TEST_DIR"
echo "  - UserMapper.xml (2개 NEXTVAL)"
echo "  - OrderMapper.xml (2개 NEXTVAL)"
echo "  - create_log.sql (1개 NEXTVAL)"
echo "  - result_no_llm.csv"
echo "  - result_no_llm.json"
echo ""
echo "LLM 분석 테스트를 하려면:"
echo "  python3 tools/extract_sequence_usage.py $TEST_DIR --output test_with_llm.csv"
echo ""
echo "정리: rm -rf $TEST_DIR"
echo ""
