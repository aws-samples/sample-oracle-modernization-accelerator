#!/bin/bash

# OMA Discovery Report Upload Script
# Application: $APPLICATION_NAME (환경 변수 사용)

# 환경 변수 설정
S3_BUCKET="s3://aws-oma-source-bucket/analysis/"
TAR_FILE="/tmp/${APPLICATION_NAME}_DiscoveryReport.tar"

echo "=== OMA Discovery Report Upload ==="
echo "Application: $APPLICATION_NAME"
echo "Source Folder: $APPLICATION_FOLDER"
echo "Target S3: $S3_BUCKET"

# 작업 디렉토리로 이동
cd "$APPLICATION_FOLDER" || {
    echo "Error: Cannot access $APPLICATION_FOLDER"
    exit 1
}

# CSV, HTML, TXT, JSON 파일 존재 확인
CSV_FILES=$(find . -name "*.csv" -type f 2>/dev/null)
HTML_FILES=$(find . -name "*.html" -type f 2>/dev/null)
TXT_FILES=$(find . -name "*.txt" -type f 2>/dev/null)
JSON_FILES=$(find . -name "*.json" -type f 2>/dev/null)

if [ -z "$CSV_FILES" ] && [ -z "$HTML_FILES" ] && [ -z "$TXT_FILES" ] && [ -z "$JSON_FILES" ]; then
    echo "Warning: No CSV, HTML, TXT, or JSON files found in $APPLICATION_FOLDER"
    echo "Creating empty tar file..."
    tar -cf "$TAR_FILE" --files-from /dev/null
else
    echo "Found files to archive:"
    find . -name "*.csv" -o -name "*.html" -o -name "*.txt" -o -name "*.json" | head -10
    
    # tar 파일 생성
    echo "Creating tar archive..."
    find . -name "*.csv" -o -name "*.html" -o -name "*.txt" -o -name "*.json" | tar -cf "$TAR_FILE" -T -
fi

# tar 파일 생성 확인
if [ ! -f "$TAR_FILE" ]; then
    echo "Error: Failed to create tar file"
    exit 1
fi

# 파일 크기 확인
TAR_SIZE=$(du -h "$TAR_FILE" | cut -f1)
echo "Archive size: $TAR_SIZE"

# S3 업로드
echo "Uploading to S3..."
aws s3 cp "$TAR_FILE" "$S3_BUCKET" || {
    echo "Error: Failed to upload to S3"
    exit 1
}

echo "✓ Successfully uploaded ${APPLICATION_NAME}_DiscoveryReport.tar to $S3_BUCKET"

# 임시 파일 정리
rm -f "$TAR_FILE"
echo "✓ Temporary files cleaned up"

echo "=== Upload Complete ==="
