#!/bin/bash

# Generate Departed XMLs (Modified Version)
# CSV 파일에서 Transform Target='Y'인 XML 파일들을 개별 Level1 요소로 분리하여 생성
# MyBatis XML Mapper 파일에서 select, insert, update, delete, sql 등의 요소를 개별 파일로 추출
# 진행 상황 추적 및 상세 요약 제공
#
# 사용법: ./genDepartedXmls.sh [타입]
# 지원되는 타입과 동작:
#   - source  : CSV에서 Transform Target='Y'인 파일들을 origin → extract (CSV 기반 소스 파일 복사 후 분리)
#   - target  : CSV에서 Transform Target='Y'인 파일들을 merge → transform (CSV 기반 타겟 파일 복사 후 분리)
#   - origin  : origin → extract (기존 원본 파일을 분리)
#   - merge   : merge → transform (기존 병합 파일을 분리)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_progress() {
    echo -e "${PURPLE}[PROGRESS]${NC} $1"
}

# 사용법 표시 함수
show_usage() {
    echo "사용법: $0 [타입]"
    echo ""
    echo "CSV 파일에서 Transform Target='Y'인 XML 파일을 개별 Level1 요소로 분리하여 생성합니다."
    echo ""
    echo "지원되는 타입:"
    echo "  $0 source    # CSV의 Transform Target='Y' XML을 origin에 복사 후 extract로 분리"
    echo "  $0 target    # CSV의 Transform Target='Y' XML을 merge에 복사 후 transform으로 분리"
    echo "  $0 origin    # 기존 origin 폴더의 XML을 extract로 분리"
    echo "  $0 merge     # 기존 merge 폴더의 XML을 transform으로 분리"
    echo ""
    echo "처리 흐름:"
    echo "  source: CSV파일 → origin(*_src.xml) → extract(개별요소)"
    echo "  target: CSV파일 → merge(*_tgt.xml) → transform(개별요소)"
    echo "  origin: origin → extract(개별요소)"
    echo "  merge:  merge → transform(개별요소)"
    echo ""
    echo "환경변수:"
    echo "  APP_LOGS_FOLDER - 애플리케이션 로그 폴더 경로 (필수)"
    echo "  APP_TRANSFORM_FOLDER - CSV 파일이 있는 transform 폴더 경로 (source/target 타입 시 필수)"
}

# 진행률 표시 함수
show_progress() {
    local current=$1
    local total=$2
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))
    
    printf "\r${CYAN}["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' '-'
    printf "] %d%% (%d/%d)${NC}" $percent $current $total
}

# 타입별 설정 함수
get_type_config() {
    local type="$1"
    
    case "$type" in
        "source")
            INPUT_FOLDER_TYPE="origin"
            OUTPUT_FOLDER_TYPE="extract"
            COPY_REQUIRED=true
            COPY_TARGET_SUBFOLDER="origin"
            COPY_FILE_SUFFIX="_src"
            ;;
        "target")
            INPUT_FOLDER_TYPE="merge"
            OUTPUT_FOLDER_TYPE="transform"
            COPY_REQUIRED=true
            COPY_TARGET_SUBFOLDER="merge"
            COPY_FILE_SUFFIX="_tgt"
            ;;
        "origin")
            INPUT_FOLDER_TYPE="origin"
            OUTPUT_FOLDER_TYPE="extract"
            COPY_REQUIRED=false
            ;;
        "merge")
            INPUT_FOLDER_TYPE="merge"
            OUTPUT_FOLDER_TYPE="transform"
            COPY_REQUIRED=false
            ;;
        *)
            return 1
            ;;
    esac
    return 0
}

# 환경변수 검증 함수
validate_environment() {
    local type="$1"
    
    if [ -z "$APP_LOGS_FOLDER" ]; then
        log_error "APP_LOGS_FOLDER 환경변수가 설정되지 않았습니다."
        return 1
    fi
    
    if [ "$type" = "source" ] || [ "$type" = "target" ]; then
        if [ -z "$APP_TRANSFORM_FOLDER" ]; then
            log_error "APP_TRANSFORM_FOLDER 환경변수가 설정되지 않았습니다."
            return 1
        fi
        
        if [ ! -f "$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv" ]; then
            log_error "CSV 파일을 찾을 수 없습니다: $APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"
            return 1
        fi
    fi
    
    return 0
}

# CSV에서 Transform Target='Y'인 파일 목록 가져오기
get_target_files_from_csv() {
    local csv_file="$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"
    
    log_info "CSV 파일에서 Transform Target='Y'인 파일들을 검색 중..."
    log_info "CSV 파일: $csv_file"
    
    # CSV에서 Transform Target이 'Y'인 행의 Filename 컬럼(2번째) 추출
    # 헤더 제외하고 처리
    local target_files=$(awk -F',' 'NR>1 && $6=="Y" {print $2}' "$csv_file" | sort)
    
    if [ -z "$target_files" ]; then
        log_warning "CSV 파일에서 Transform Target='Y'인 파일을 찾을 수 없습니다."
        return 1
    fi
    
    local file_count=$(echo "$target_files" | wc -l)
    log_info "CSV에서 $file_count 개의 대상 파일을 찾았습니다."
    
    echo "$target_files"
    return 0
}

# CSV 기반 파일 복사 함수 (source/target용)
copy_files_from_csv() {
    log_info "CSV 기반 파일 복사 작업을 시작합니다..."
    log_info "대상 서브폴더: $COPY_TARGET_SUBFOLDER"
    log_info "파일 접미사: $COPY_FILE_SUFFIX"
    
    # CSV에서 대상 파일 목록 가져오기
    local target_files
    if ! target_files=$(get_target_files_from_csv); then
        return 1
    fi
    
    local copy_count=0
    local copy_success=0
    local copy_errors=0
    local copy_not_found=0
    
    while IFS= read -r source_file; do
        copy_count=$((copy_count + 1))
        
        # 파일 존재 확인
        if [ ! -f "$source_file" ]; then
            log_warning "파일이 존재하지 않습니다: $source_file"
            copy_not_found=$((copy_not_found + 1))
            continue
        fi
        
        # 파일명과 디렉토리 정보 추출
        local filename=$(basename "$source_file" .xml)
        local relative_dir=$(dirname "$source_file" | sed 's|.*/resources/||')
        
        # 대상 디렉토리 생성
        local target_dir="$BASE_PATH/$relative_dir/$filename/$COPY_TARGET_SUBFOLDER"
        local target_file="$target_dir/${filename}${COPY_FILE_SUFFIX}.xml"
        
        log_progress "복사 중 [$copy_count]: $filename"
        
        # 디렉토리 생성
        if ! mkdir -p "$target_dir"; then
            log_error "디렉토리 생성 실패: $target_dir"
            copy_errors=$((copy_errors + 1))
            continue
        fi
        
        # 파일 복사
        if cp "$source_file" "$target_file"; then
            copy_success=$((copy_success + 1))
            log_success "복사 완료: $filename → $target_file"
        else
            log_error "파일 복사 실패: $source_file → $target_file"
            copy_errors=$((copy_errors + 1))
        fi
        
    done <<< "$target_files"
    
    echo
    log_info "CSV 기반 파일 복사 작업 완료"
    log_info "총 처리: $copy_count, 성공: $copy_success, 실패: $copy_errors, 파일없음: $copy_not_found"
    echo
    
    if [ $copy_errors -gt 0 ]; then
        return 1
    fi
    
    return 0
}

# 인자 확인
if [ $# -ne 1 ]; then
    log_error "잘못된 인자 개수입니다."
    echo
    show_usage
    exit 1
fi

TYPE="$1"

# 지원되는 타입 확인 및 설정
SUPPORTED_TYPES=("source" "target" "origin" "merge")
if [[ ! " ${SUPPORTED_TYPES[@]} " =~ " ${TYPE} " ]]; then
    log_error "지원되지 않는 타입: $TYPE"
    echo
    show_usage
    exit 1
fi

# 타입별 설정 가져오기
if ! get_type_config "$TYPE"; then
    log_error "타입 설정을 가져오는데 실패했습니다: $TYPE"
    exit 1
fi

# 환경변수 검증
if ! validate_environment "$TYPE"; then
    echo
    show_usage
    exit 1
fi

# 시작 시간 기록
start_time=$(date +%s)

# 스크립트 시작
echo "========================================================"
log_info "Generate Departed XMLs 배치 실행을 시작합니다... (CSV 기반)"
log_info "처리 타입: $TYPE"
log_info "입력 폴더: $INPUT_FOLDER_TYPE"
log_info "출력 폴더: $OUTPUT_FOLDER_TYPE"
if [ "$COPY_REQUIRED" = true ]; then
    log_info "복사 작업: 필요 (CSV Transform Target='Y' → ${COPY_TARGET_SUBFOLDER})"
else
    log_info "복사 작업: 불필요"
fi
log_info "작업: XML 파일을 개별 Level1 요소로 분리"
echo "========================================================"

# 기본 경로 설정
BASE_PATH="$APP_LOGS_FOLDER/SQLTransformTarget/mapper"
EXTRACTOR_PATH="/home/ec2-user/workspace/sample-oracle-modernization-accelerator/bin/application/xmlExtractor.py"

# 통계 변수
total_files=0
success_files=0
error_files=0
total_elements=0
declare -a error_list=()
declare -a success_details=()

# xmlExtractor.py 파일 존재 확인
if [ ! -f "$EXTRACTOR_PATH" ]; then
    log_error "xmlExtractor.py 파일을 찾을 수 없습니다: $EXTRACTOR_PATH"
    exit 1
fi

log_info "XML 추출기 경로: $EXTRACTOR_PATH"
log_info "기본 경로: $BASE_PATH (APP_LOGS_FOLDER: $APP_LOGS_FOLDER)"
echo

# source/target인 경우 CSV 기반 파일 복사 작업 수행
if [ "$COPY_REQUIRED" = true ]; then
    if ! copy_files_from_csv; then
        log_error "CSV 기반 파일 복사 작업 중 오류가 발생했습니다."
        exit 1
    fi
fi

# 지정된 폴더의 모든 XML 파일 찾기
log_info "분리할 XML 파일들을 검색 중..."
xml_files=$(find "$BASE_PATH" -path "*/${INPUT_FOLDER_TYPE}/*.xml" | sort)
search_pattern="$BASE_PATH/*/${INPUT_FOLDER_TYPE}/*.xml"

if [ -z "$xml_files" ]; then
    log_warning "분리할 XML 파일을 찾을 수 없습니다."
    log_info "검색 경로: $search_pattern"
    exit 0
fi

# 찾은 파일 개수 출력
file_count=$(echo "$xml_files" | wc -l)
log_info "총 $file_count 개의 XML 파일을 개별 요소로 분리합니다."
echo

# 각 XML 파일 처리
while IFS= read -r xml_file; do
    total_files=$((total_files + 1))
    
    # 진행률 표시
    show_progress $total_files $file_count
    
    # 출력 폴더 경로 생성
    output_dir=$(dirname "$xml_file" | sed "s/${INPUT_FOLDER_TYPE}$/${OUTPUT_FOLDER_TYPE}/")
    
    # 파일명 추출 (경로 제거)
    filename=$(basename "$xml_file")
    
    echo # 새 줄
    log_progress "[$total_files/$file_count] 분리 중: $filename"
    
    # 출력 디렉토리가 존재하지 않으면 생성
    if [ ! -d "$output_dir" ]; then
        mkdir -p "$output_dir"
    fi
    
    # xmlExtractor.py 실행 및 결과 캡처
    output=$(python3 "$EXTRACTOR_PATH" -i "$xml_file" -o "$output_dir" --log-level INFO 2>&1)
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success_files=$((success_files + 1))
        
        # 추출된 요소 개수 파싱
        elements=$(echo "$output" | grep -o "Extracted [0-9]* Level1 elements" | grep -o "[0-9]*" | head -1)
        if [ -n "$elements" ]; then
            total_elements=$((total_elements + elements))
            success_details+=("$filename: $elements 개 요소로 분리")
        else
            success_details+=("$filename: 분리 완료")
        fi
        
        log_success "완료: $filename"
    else
        error_files=$((error_files + 1))
        error_list+=("$filename: $output")
        log_error "실패: $filename"
    fi
    
done <<< "$xml_files"

# 마지막 진행률 표시 완료
echo
echo

# 종료 시간 기록
end_time=$(date +%s)
duration=$((end_time - start_time))

# 최종 결과 출력
echo "========================================================"
log_info "Generate Departed XMLs 배치 실행 완료 (CSV 기반)"
echo "========================================================"
log_info "처리 타입: $TYPE"
log_info "입력 폴더: $INPUT_FOLDER_TYPE"
log_info "출력 폴더: $OUTPUT_FOLDER_TYPE"
log_info "실행 시간: ${duration}초"
log_info "총 처리 파일: $total_files"
log_success "성공: $success_files"
log_info "총 생성된 개별 XML: $total_elements"

if [ $error_files -gt 0 ]; then
    log_error "실패: $error_files"
    echo
    log_error "실패한 파일 목록:"
    for error in "${error_list[@]}"; do
        echo "  - $error"
    done
else
    log_info "실패: $error_files"
fi

echo
log_info "성공한 파일 상세 정보:"
for detail in "${success_details[@]}"; do
    echo "  - $detail"
done

echo "========================================================"

# 종료 코드 설정
if [ $error_files -gt 0 ]; then
    exit 1
else
    exit 0
fi
