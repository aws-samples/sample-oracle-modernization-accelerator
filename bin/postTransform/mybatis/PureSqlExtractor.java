import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;
import java.io.*;
import java.util.*;

public class PureSqlExtractor {
    
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java PureSqlExtractor <xml-file-path> [statement-id]");
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
                        
                        // 요소의 모든 텍스트 내용 추출 (동적 태그 처리 포함)
                        String sqlContent = getTextContent(element);
                        
                        // 파라미터 치환
                        String finalSql = substituteParameters(sqlContent);
                        
                        // 공백 정리
                        finalSql = finalSql.replaceAll("\\s+", " ").trim();
                        
                        System.out.println("Generated SQL:");
                        
                        // SQL 길이 확인
                        System.out.println("SQL Length: " + finalSql.length());
                        
                        // SQL을 임시 파일에 저장 (화면 출력 버퍼 문제 해결)
                        String tempFileName = "/tmp/sql_output_" + System.currentTimeMillis() + ".sql";
                        try (java.io.FileWriter writer = new java.io.FileWriter(tempFileName)) {
                            writer.write(finalSql);
                            System.out.println("Generated SQL:");
                            System.out.println("SQL Length: " + finalSql.length());
                            System.out.println("SQL_FILE:" + tempFileName);
                        } catch (java.io.IOException e) {
                            System.err.println("파일 저장 실패: " + e.getMessage());
                            // 파일 저장 실패시 기존 방식으로 출력
                            System.out.println(finalSql);
                        }
                        System.out.println();
                        
                        // 디버그 메시지 제거 (파일로 저장하므로 불필요)
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
                String nodeValue = child.getNodeValue();
                if (nodeValue != null) {
                    content.append(nodeValue);
                }
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
    
    private static String substituteParameters(String sql) {
        // 파라미터 파일에서 관리할 파라미터들 (타입 정보가 없는 것들)
        Map<String, String> parameterFile = new HashMap<>();
        parameterFile.put("orderby", "1");                    // 숫자
        parameterFile.put("saletype", "DEFAULT");             // 문자
        parameterFile.put("virtualrsvno", "DEFAULT");         // 문자
        parameterFile.put("agtCd", "TEST");                   // 문자
        parameterFile.put("diFlag", "Y");                     // 문자
        parameterFile.put("saledeptcd", "TEST");              // 문자
        parameterFile.put("rsvDtm", "20240101");              // 날짜(문자)
        parameterFile.put("inicisjoinyn", "Y");               // 문자
        parameterFile.put("superrsvno", "SUPER001");          // 문자
        parameterFile.put("grpmastrseqno", "1");              // 숫자
        parameterFile.put("grpdetailseqno", "1");             // 숫자
        parameterFile.put("ifsysrsvno", "IF001");             // 문자
        
        String result = sql;
        
        // 1. #{...} 패턴 처리
        java.util.regex.Pattern hashPattern = java.util.regex.Pattern.compile("#\\{([^}]+)\\}");
        java.util.regex.Matcher hashMatcher = hashPattern.matcher(result);
        StringBuffer hashBuffer = new StringBuffer();
        
        while (hashMatcher.find()) {
            String fullMatch = hashMatcher.group(1);
            String paramName = fullMatch.split(",")[0].trim();
            
            String replacement;
            if (fullMatch.contains("jdbcType=VARCHAR")) {
                // VARCHAR 타입은 파라미터명을 대문자로 변환하여 문자열로 처리
                replacement = "'" + paramName.toUpperCase() + "'";
            } else if (fullMatch.contains("jdbcType=INTEGER")) {
                // INTEGER 타입은 숫자 1로 처리
                replacement = "1";
            } else if (fullMatch.contains("typeHandler=")) {
                // typeHandler가 있는 경우 (암호화 필드 등) 문자열로 처리
                replacement = "'" + paramName.toUpperCase() + "'";
            } else if (parameterFile.containsKey(paramName)) {
                // 파라미터 파일에 있는 경우 값의 형태로 타입 추정
                String value = parameterFile.get(paramName);
                if (isNumeric(value)) {
                    replacement = value;  // 숫자는 따옴표 없이
                } else {
                    replacement = "'" + value + "'";  // 문자/날짜는 따옴표로 감싸기
                }
            } else {
                // 기타 경우 기본적으로 문자열로 처리
                replacement = "'" + paramName.toUpperCase() + "'";
            }
            
            hashMatcher.appendReplacement(hashBuffer, java.util.regex.Matcher.quoteReplacement(replacement));
        }
        hashMatcher.appendTail(hashBuffer);
        result = hashBuffer.toString();
        
        // 2. ${...} 패턴 처리
        java.util.regex.Pattern dollarPattern = java.util.regex.Pattern.compile("\\$\\{([^}]+)\\}");
        java.util.regex.Matcher dollarMatcher = dollarPattern.matcher(result);
        StringBuffer dollarBuffer = new StringBuffer();
        
        while (dollarMatcher.find()) {
            String paramName = dollarMatcher.group(1).trim();
            
            String replacement;
            if (parameterFile.containsKey(paramName)) {
                replacement = parameterFile.get(paramName);
            } else {
                replacement = paramName.toUpperCase();
            }
            
            dollarMatcher.appendReplacement(dollarBuffer, java.util.regex.Matcher.quoteReplacement(replacement));
        }
        dollarMatcher.appendTail(dollarBuffer);
        result = dollarBuffer.toString();
        
        return result;
    }
    
    // 숫자 여부 판단 헬퍼 메서드
    private static boolean isNumeric(String str) {
        try {
            Integer.parseInt(str);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }
}
