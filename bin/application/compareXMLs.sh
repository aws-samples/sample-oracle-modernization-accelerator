#!/bin/bash

# XML 파일 비교 도구
# Usage: compareXMLs.sh

# 환경 변수 확인
if [ -z "$APP_LOGS_FOLDER" ]; then
    echo "Error: APP_LOGS_FOLDER must be set"
    exit 1
fi

# Source와 Target 폴더 설정 (모든 extract/transform 폴더)
SOURCE_FOLDERS=($(find "$APP_LOGS_FOLDER/mapper" -type d -name "*extract*"))
TARGET_FOLDERS=($(find "$APP_LOGS_FOLDER/mapper" -type d -name "*transform*"))

if [ ${#SOURCE_FOLDERS[@]} -eq 0 ] || [ ${#TARGET_FOLDERS[@]} -eq 0 ]; then
    echo "Error: Could not find extract or transform folders in $APP_LOGS_FOLDER/mapper"
    echo "Available folders:"
    find "$APP_LOGS_FOLDER/mapper" -type d 2>/dev/null | head -10
    exit 1
fi

while true; do
    echo ""
    echo "=== XML File Comparison Tool ==="
    echo "Searching in ${#SOURCE_FOLDERS[@]} extract folders and ${#TARGET_FOLDERS[@]} transform folders"
    echo ""
    
    # XML 파일 이름 입력 받기
    read -p "Enter XML filename to search (or 'quit'/'q' to exit): " xml_name
    
    if [ "$xml_name" = "quit" ] || [ "$xml_name" = "q" ]; then
        echo "Goodbye!"
        break
    fi
    
    if [ -z "$xml_name" ]; then
        echo "Please enter a filename"
        continue
    fi
    
    # 모든 Source 폴더에서 XML 파일 검색
    echo ""
    echo "Searching for '*${xml_name}*' in all extract and transform folders..."
    
    # 파일명으로 검색
    source_files_by_name=()
    for folder in "${SOURCE_FOLDERS[@]}"; do
        while IFS= read -r -d '' file; do
            source_files_by_name+=("$file")
        done < <(find "$folder" -name "*${xml_name}*.xml" -type f -print0 2>/dev/null)
    done
    
    # 내용으로 검색 (SQL ID 등)
    source_files_by_content=()
    for folder in "${SOURCE_FOLDERS[@]}"; do
        while IFS= read -r -d '' file; do
            source_files_by_content+=("$file")
        done < <(find "$folder" -name "*.xml" -type f -exec grep -l "${xml_name}" {} \; -print0 2>/dev/null)
    done
    
    # 결과 합치기 (중복 제거)
    source_files=($(printf '%s\n' "${source_files_by_name[@]}" "${source_files_by_content[@]}" | sort -u))
    
    if [ ${#source_files[@]} -eq 0 ]; then
        echo "No XML files found matching '*${xml_name}*' in source folder"
        continue
    fi
    
    # 매칭되는 파일 쌍 찾기
    declare -a pairs
    pair_count=0
    
    for source_file in "${source_files[@]}"; do
        if [ -z "$source_file" ]; then
            continue
        fi
        
        source_basename=$(basename "$source_file")
        
        # src를 tgt로 변경하여 target 파일명 생성
        target_basename=$(echo "$source_basename" | sed 's/src/tgt/g')
        
        # 모든 Target 폴더에서 해당 파일 찾기
        target_file=""
        for target_folder in "${TARGET_FOLDERS[@]}"; do
            found_file=$(find "$target_folder" -name "$target_basename" -type f | head -1)
            if [ -n "$found_file" ]; then
                target_file="$found_file"
                break
            fi
        done
        
        if [ -n "$target_file" ] && [ -f "$target_file" ]; then
            pairs[$pair_count]="$source_file|$target_file"
            ((pair_count++))
        fi
    done
    
    if [ $pair_count -eq 0 ]; then
        echo "No matching XML file pairs found"
        echo ""
        echo "Source files found:"
        for source_file in "${source_files[@]}"; do
            if [ -n "$source_file" ]; then
                echo "  $(basename "$source_file")"
            fi
        done
        continue
    fi
    
    # 매칭된 파일 쌍 표시
    echo ""
    echo "Found ${pair_count} matching XML file pair(s):"
    echo ""
    
    for i in "${!pairs[@]}"; do
        IFS='|' read -r source_file target_file <<< "${pairs[$i]}"
        source_basename=$(basename "$source_file")
        target_basename=$(basename "$target_file")
        echo "$((i+1)). $source_basename -> $target_basename"
        echo "   Source: $source_file"
        echo "   Target: $target_file"
        echo ""
    done
    
    # 파일 선택
    while true; do
        read -p "Select file number to compare (1-${pair_count}) or 'back'/'b' to search again: " selection
        
        if [ "$selection" = "back" ] || [ "$selection" = "b" ]; then
            break
        fi
        
        # 숫자 검증 및 범위 체크
        if [[ "$selection" =~ ^[0-9]+$ ]]; then
            if [ "$selection" -ge 1 ] && [ "$selection" -le "$pair_count" ]; then
                # 선택된 파일 쌍 가져오기
                selected_pair="${pairs[$((selection-1))]}"
                IFS='|' read -r source_file target_file <<< "$selected_pair"
                
                echo ""
                echo "Comparing:"
                echo "Source: $source_file"
                echo "Target: $target_file"
                echo ""
                echo "Press SPACE for next page, 'q' to quit the diff viewer"
                echo ""
                
                # git diff로 비교
                git diff --no-index --color=always "$source_file" "$target_file" | more
                
                echo ""
                echo "Comparison completed."
                break
            else
                echo "Invalid selection. Please enter a number between 1 and ${pair_count}"
            fi
        else
            echo "Invalid input. Please enter a number or 'back'"
        fi
    done
    
    # pairs 배열 초기화
    unset pairs
done
