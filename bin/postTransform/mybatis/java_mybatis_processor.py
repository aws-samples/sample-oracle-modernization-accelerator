#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java MyBatis 파서 기반 동적 처리기
"""

import subprocess
import os
import logging
import tempfile
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class JavaMyBatisProcessor:
    """Java MyBatis 파서를 사용한 동적 SQL 처리기"""
    
    def __init__(self):
        # 현재 스크립트 위치 기준으로 mybatis 디렉토리 내의 PureSqlExtractor 사용
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.java_extractor_path = os.path.join(current_dir, "PureSqlExtractor")
        self.mybatis_dir = current_dir
        self.ensure_java_compiled()
        
    def ensure_java_compiled(self):
        """Java 파서가 컴파일되어 있는지 확인"""
        if not os.path.exists(f"{self.java_extractor_path}.class"):
            logger.error("Java 파서가 컴파일되지 않았습니다. /tmp/PureSqlExtractor.class를 확인하세요.")
            
    def process_dynamic_conditions(self, content: str, xml_file_path: str = None) -> str:
        """동적 조건 처리 - Java 파서 사용"""
        
        if xml_file_path and os.path.exists(xml_file_path):
            # XML 파일이 있으면 Java 파서 직접 사용
            return self._parse_with_java(xml_file_path)
        else:
            # XML 파일이 없으면 임시 파일 생성 후 처리
            return self._parse_content_with_java(content)
    
    def _parse_with_java(self, xml_file_path: str, statement_id: str = None) -> str:
        """Java 파서로 XML 파일 직접 파싱"""
        
        try:
            cmd = ["java", "-cp", self.mybatis_dir, "PureSqlExtractor", xml_file_path]
            if statement_id:
                cmd.append(statement_id)
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.mybatis_dir
            )
            
            if result.returncode == 0:
                logger.debug(f"Java 파서 원본 출력:\n{result.stdout}")
                sql = self._extract_sql_from_output(result.stdout)
                logger.debug(f"추출된 SQL: {sql}")
                if sql:
                    logger.info("Java 파서로 SQL 생성 완료")
                    return sql
                else:
                    logger.warning("Java 파서에서 SQL을 추출할 수 없음")
                    return self._fallback_processing(xml_file_path)
            else:
                logger.error(f"Java 파서 실행 실패: {result.stderr}")
                return self._fallback_processing(xml_file_path)
                
        except subprocess.TimeoutExpired:
            logger.error("Java 파서 실행 시간 초과")
            return self._fallback_processing(xml_file_path)
        except Exception as e:
            logger.error(f"Java 파서 실행 중 오류: {e}")
            return self._fallback_processing(xml_file_path)
    
    def _parse_content_with_java(self, content: str) -> str:
        """내용을 임시 XML 파일로 만들어 Java 파서 사용"""
        
        try:
            # 임시 XML 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as temp_file:
                # 완전한 XML 구조로 래핑
                xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<mapper namespace="temp.mapper">
    <select id="tempSelect" resultType="map">
        {content}
    </select>
</mapper>'''
                temp_file.write(xml_content)
                temp_file_path = temp_file.name
            
            # Java 파서로 처리
            result = self._parse_with_java(temp_file_path, "tempSelect")
            
            # 임시 파일 삭제
            os.unlink(temp_file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"임시 파일 처리 중 오류: {e}")
            return self._fallback_processing_content(content)
    
    def _extract_sql_from_output(self, output: str) -> Optional[str]:
        """Java 파서 출력에서 SQL 추출 - 파일 기반 방식"""
        
        lines = output.split('\n')
        
        # SQL_FILE: 경로를 찾기
        for line in lines:
            if line.startswith("SQL_FILE:"):
                file_path = line.replace("SQL_FILE:", "").strip()
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        sql_content = f.read().strip()
                    
                    # 임시 파일 삭제
                    import os
                    try:
                        os.remove(file_path)
                    except:
                        pass  # 삭제 실패해도 무시
                    
                    if sql_content:
                        logger.info(f"파일에서 SQL 읽기 성공: {len(sql_content)}자")
                        return sql_content
                        
                except Exception as e:
                    logger.error(f"SQL 파일 읽기 실패: {e}")
        
        # 파일 방식 실패시 기존 방식으로 fallback
        logger.warning("파일 방식 실패, stdout 파싱으로 fallback")
        return self._extract_sql_from_stdout(output)
    
    def _extract_sql_from_stdout(self, output: str) -> Optional[str]:
        """기존 stdout 파싱 방식 (fallback용)"""
        
        lines = output.split('\n')
        sql_started = False
        sql_parts = []
        
        for line in lines:
            if line.strip() == "Generated SQL:":
                sql_started = True
                continue
            elif sql_started:
                # SQL Length 라인 건너뛰기
                if line.startswith("SQL Length:") or line.startswith("SQL_FILE:"):
                    continue
                # 종료 조건들
                if (line.strip() == "" or 
                    line.startswith("✓") or 
                    line.startswith("❌") or
                    line.startswith("PTN_PROMTN_SUM_AMT") or
                    line.startswith("===")):
                    break
                sql_parts.append(line.strip())
        
        if sql_parts:
            return ' '.join(sql_parts).strip()
        
        return None
    
    def _fallback_processing(self, xml_file_path: str) -> str:
        """Java 파서 실패시 fallback 처리"""
        
        logger.info("Java 파서 실패, Python fallback 처리")
        
        try:
            with open(xml_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._fallback_processing_content(content)
        except Exception as e:
            logger.error(f"Fallback 처리 실패: {e}")
            return ""
    
    def _fallback_processing_content(self, content: str) -> str:
        """내용에 대한 fallback 처리"""
        
        # 기존 Python 처리기 사용
        try:
            from .learning_parameter_processor import LearningParameterProcessor
            processor = LearningParameterProcessor()
            return processor.process_content_with_learning(content)
        except Exception as e:
            logger.error(f"Python fallback 처리 실패: {e}")
            return content
