#!/bin/bash

# TKPROF 기본 사용법
# tkprof trace_file output_file [options]

# 예시: 기본 분석
tkprof /path/to/tracefile.trc output_report.txt

# 예시: 상세 분석 (SQL 정렬, 실행계획 포함)
tkprof /path/to/tracefile.trc detailed_report.txt \
  sort=prsela,exeela,fchela \
  sys=no \
  explain=<username>/<password> \
  aggregate=no

# 주요 옵션 설명:
# sort=prsela,exeela,fchela : Parse, Execute, Fetch 시간 순으로 정렬
# sys=no : 시스템 SQL 제외
# explain=user/pass : 실행계획 포함
# aggregate=no : 동일 SQL 통합하지 않음
