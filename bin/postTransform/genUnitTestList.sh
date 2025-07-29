#!/bin/bash

# XML 파일 리스트 생성 및 변환 스크립트

echo "=== XML 파일 리스트 생성 시작 ==="

# 1. target_xml.lst 생성
echo "1. $APP_LOGS_FOLDER/mapper/*/transform/*xml 리스트를 $APP_TRANSFORM_FOLDER/target_xml.lst 로 작성"
find $APP_LOGS_FOLDER/mapper/ -path "*/transform/*.xml" > $APP_TRANSFORM_FOLDER/target_xml.lst
TARGET_COUNT=$(wc -l < $APP_TRANSFORM_FOLDER/target_xml.lst)
echo "   생성된 target XML 파일 수: $TARGET_COUNT"

# 2. source_xml.lst 생성 (_tgt -> _src, transform -> extract 경로 변경)
echo "2. target_xml.lst의 _tgt를 _src로, transform을 extract로 변경하여 source_xml.lst 생성"
sed 's/_tgt/_src/g; s/\/transform\//\/extract\//g' $APP_TRANSFORM_FOLDER/target_xml.lst > $APP_TRANSFORM_FOLDER/source_xml.lst
SOURCE_COUNT=$(wc -l < $APP_TRANSFORM_FOLDER/source_xml.lst)
echo "   생성된 source XML 파일 수: $SOURCE_COUNT"

# 3. 전체 파일 수 비교 로그
echo "3. 파일 수 비교 결과:"
echo "   Target XML 파일 수: $TARGET_COUNT"
echo "   Source XML 파일 수: $SOURCE_COUNT"

if [ $TARGET_COUNT -eq $SOURCE_COUNT ]; then
    echo "   ✓ 파일 수가 일치합니다."
else
    echo "   ⚠ 파일 수가 일치하지 않습니다!"
fi

echo "=== 작업 완료 ==="
echo "생성된 파일:"
echo "  - $APP_TRANSFORM_FOLDER/target_xml.lst"
echo "  - $APP_TRANSFORM_FOLDER/source_xml.lst"
