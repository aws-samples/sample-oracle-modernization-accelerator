---
layout: page
title: UI 오류 수정
nav_order: 10
has_children: true
description: "UI 관련 XML 오류 수정 작업"
---

# UI 오류 수정

변환 과정에서 발생한 UI 관련 XML 오류를 자동으로 수정하는 작업입니다.

## 개요

Oracle에서 PostgreSQL/MySQL로 변환하는 과정에서 MyBatis Mapper XML 파일에는 다양한 UI 관련 오류가 발생할 수 있습니다. 이러한 오류들을 Amazon Q Chat을 활용하여 지능적으로 분석하고 자동으로 수정합니다.

## 주요 기능

- **AI 기반 오류 분석**: Amazon Q Chat을 통한 지능형 오류 패턴 분석
- **자동 수정 제안**: 일반적인 UI 오류에 대한 자동 수정 방안 제시
- **Target DB별 최적화**: PostgreSQL/MySQL 특화 오류 처리
- **안전한 백업**: 원본 파일 자동 백업으로 안전성 확보

## 처리 대상

### UI 관련 오류 유형
- SQL 구문 오류 (Oracle 특화 함수 사용 등)
- 파라미터 바인딩 오류 (#{} vs ${} 사용법)
- 결과 매핑 오류 (resultMap 불일치)
- 동적 SQL 오류 (조건문, 반복문 구문)

### Target DB별 특화 오류
- **PostgreSQL**: 대소문자 구분, 스키마명, 시퀀스 사용법
- **MySQL**: 백틱 사용, 날짜 함수, AUTO_INCREMENT

## 문서 목록

- **[5-1. UI 오류-XML 재수정](5-1.processUIErrorXMLFix.md)**: UI 관련 XML 오류 재수정 작업
