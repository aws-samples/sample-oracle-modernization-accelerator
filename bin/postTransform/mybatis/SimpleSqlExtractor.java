import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.mapping.SqlSource;
import org.apache.ibatis.scripting.xmltags.DynamicSqlSource;
import org.apache.ibatis.scripting.xmltags.SqlNode;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;
import java.io.*;
import java.util.*;

public class SimpleSqlExtractor {
    
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java SimpleSqlExtractor <xml-file-path> [statement-id]");
            System.exit(1);
        }
        
        String xmlFilePath = args[0];
        String targetStatementId = args.length > 1 ? args[1] : null;
        
        try {
            // DOM 파서로 XML 직접 파싱
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(new File(xmlFilePath));
            
            // select, insert, update, delete 요소들 찾기
            String[] sqlTags = {"select", "insert", "update", "delete"};
            
            for (String tagName : sqlTags) {
                NodeList nodes = doc.getElementsByTagName(tagName);
                
                for (int i = 0; i < nodes.getLength(); i++) {
                    Element element = (Element) nodes.item(i);
                    String id = element.getAttribute("id");
                    
                    // 특정 statement만 처리하거나 모든 statement 처리
                    if (targetStatementId == null || id.contains(targetStatementId)) {
                        
                        System.out.println("=== Statement: " + id + " ===");
                        System.out.println("Type: " + tagName.toUpperCase());
                        
                        // 요소의 모든 텍스트 내용 추출
                        String sqlContent = getTextContent(element);
                        
                        // 간단한 동적 태그 처리
                        String processedSql = processSimpleDynamicTags(sqlContent);
                        
                        // 파라미터 치환
                        String finalSql = substituteParameters(processedSql);
                        
                        // 공백 정리
                        finalSql = finalSql.replaceAll("\\s+", " ").trim();
                        
                        System.out.println("Generated SQL:");
                        System.out.println(finalSql);
                        System.out.println();
                        
                        // 문제 패턴 확인
                        if (finalSql.contains("0 ) , 0)")) {
                            System.out.println("❌ 문제 패턴 발견!");
                            int pos = finalSql.indexOf("0 ) , 0)");
                            int start = Math.max(0, pos - 100);
                            int end = Math.min(finalSql.length(), pos + 100);
                            System.out.println("문제 구간: " + finalSql.substring(start, end));
                        } else {
                            System.out.println("✓ 문제 패턴 없음");
                        }
                    }
                }
            }
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private static String getTextContent(Element element) {
        StringBuilder content = new StringBuilder();
        NodeList children = element.getChildNodes();
        
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            
            if (child.getNodeType() == Node.TEXT_NODE || 
                child.getNodeType() == Node.CDATA_SECTION_NODE) {
                content.append(child.getNodeValue());
            } else if (child.getNodeType() == Node.ELEMENT_NODE) {
                Element childElement = (Element) child;
                String tagName = childElement.getTagName();
                
                // 동적 태그들은 특별 처리
                if ("if".equals(tagName)) {
                    String test = childElement.getAttribute("test");
                    if (shouldIncludeIf(test)) {
                        content.append(getTextContent(childElement));
                    }
                } else if ("choose".equals(tagName)) {
                    content.append(processChoose(childElement));
                } else if ("where".equals(tagName)) {
                    String whereContent = getTextContent(childElement).trim();
                    if (!whereContent.isEmpty()) {
                        // 앞의 AND/OR 제거
                        whereContent = whereContent.replaceAll("^\\s*(AND|OR)\\s+", "");
                        content.append(" WHERE ").append(whereContent);
                    }
                } else if ("foreach".equals(tagName)) {
                    content.append(processForeach(childElement));
                } else {
                    // 일반 요소는 내용만 추가
                    content.append(getTextContent(childElement));
                }
            }
        }
        
        return content.toString();
    }
    
    private static boolean shouldIncludeIf(String test) {
        // 간단한 조건 평가
        if (test.contains("!= null") || test.contains("!= \"\"") || test.contains("!= ''")) {
            return true; // 대부분의 조건을 true로 가정
        }
        if (test.contains("== null") || test.contains("== \"\"") || test.contains("== ''")) {
            return false;
        }
        return true; // 기본적으로 true
    }
    
    private static String processChoose(Element chooseElement) {
        NodeList children = chooseElement.getChildNodes();
        
        // 첫 번째 when을 선택
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE) {
                Element childElement = (Element) child;
                if ("when".equals(childElement.getTagName())) {
                    return getTextContent(childElement);
                }
            }
        }
        
        // when이 없으면 otherwise 찾기
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE) {
                Element childElement = (Element) child;
                if ("otherwise".equals(childElement.getTagName())) {
                    return getTextContent(childElement);
                }
            }
        }
        
        return "";
    }
    
    private static String processForeach(Element foreachElement) {
        String collection = foreachElement.getAttribute("collection");
        String item = foreachElement.getAttribute("item");
        String separator = foreachElement.getAttribute("separator");
        String open = foreachElement.getAttribute("open");
        String close = foreachElement.getAttribute("close");
        
        if (separator.isEmpty()) separator = ",";
        if (open.isEmpty()) open = "(";
        if (close.isEmpty()) close = ")";
        
        String content = getTextContent(foreachElement);
        
        // 3개 항목으로 시뮬레이션
        StringBuilder result = new StringBuilder(open);
        for (int i = 0; i < 3; i++) {
            if (i > 0) result.append(separator);
            String itemContent = content.replaceAll("#\\{" + item + "\\}", "'DEFAULT" + (i+1) + "'");
            itemContent = itemContent.replaceAll("\\$\\{" + item + "\\}", "DEFAULT" + (i+1));
            result.append(itemContent);
        }
        result.append(close);
        
        return result.toString();
    }
    
    private static String processSimpleDynamicTags(String sql) {
        // CDATA 섹션 제거
        sql = sql.replaceAll("<!\\[CDATA\\[", "").replaceAll("\\]\\]>", "");
        
        return sql;
    }
    
    private static String substituteParameters(String sql) {
        Map<String, String> params = new HashMap<>();
        params.put("agtCd", "TEST");
        params.put("diFlag", "Y");
        params.put("saletype", "DEFAULT");
        params.put("virtualrsvno", "DEFAULT");
        params.put("saledeptcd", "TEST");
        params.put("orderby", "1");
        params.put("inicisjoinyn", "Y");
        params.put("rsvDtm", "20240101");
        
        String result = sql;
        
        for (Map.Entry<String, String> entry : params.entrySet()) {
            String param = entry.getKey();
            String value = entry.getValue();
            
            // #{param} 패턴
            result = result.replaceAll("#\\{" + param + "(?:,[^}]*)?" + "\\}", "'" + value + "'");
            
            // ${param} 패턴
            result = result.replaceAll("\\$\\{" + param + "(?:,[^}]*)?" + "\\}", value);
        }
        
        return result;
    }
}
