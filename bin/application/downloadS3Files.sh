#!/bin/bash

# S3 버킷에서 파일들을 현재 디렉토리로 다운로드
echo "S3에서 파일 다운로드 시작..."

# 다운로드 전 현재 파일 목록 저장
ls -la > /tmp/before_download.txt

# s3://aws-oma-source-bucket/oma-source/ 의 모든 파일을 현재 디렉토리로 동기화
aws s3 sync s3://aws-oma-source-bucket/oma-source/ ./

echo "다운로드 완료!"
echo ""
echo "=== 다운로드한 파일 목록 ==="
ls -la | grep -v "^total"
echo ""
echo "=== 새로 추가된 파일들 ==="
ls -la > /tmp/after_download.txt
diff /tmp/before_download.txt /tmp/after_download.txt | grep "^>" | sed 's/^> //'
