package com.test.mybatis;

import org.w3c.dom.*;
import org.xml.sax.SAXException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.io.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * MyBatis XML 분석 및 테스트 준비 프로그램
 * XML 파일에서 SQL ID를 찾고, 파라미터를 분석하여 테스트용 파일을 생성합니다.
 */
public class MyBatisTestPreparator {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("사용법: java MyBatisTestPreparator <XML파일경로> <SQLID>");
            System.out.println("예시: java MyBatisTestPreparator /home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper/inventory/InventoryMapper.xml selectInventoryStatusAnalysis");
            return;
        }
        
        String xmlFilePath = args[0];
        String sqlId = args[1];
        
        MyBatisTestPreparator preparator = new MyBatisTestPreparator();
        preparator.analyzeAndPrepare(xmlFilePath, sqlId);
    }
    
    public void analyzeAndPrepare(String xmlFilePath, String sqlId) {
        try {
            System.out.println("=== MyBatis XML 분석 시작 ===");
            System.out.println("XML 파일: " + xmlFilePath);
            System.out.println("SQL ID: " + sqlId);
            
            // 1. XML 파일 읽기 및 SQL ID 찾기
            Document document = parseXmlFile(xmlFilePath);
            Element sqlElement = findSqlElement(document, sqlId);
            
            if (sqlElement == null) {
                System.err.println("SQL ID '" + sqlId + "'를 찾을 수 없습니다.");
                return;
            }
            
            // 2. SQL 내용 추출
            String sqlContent = extractSqlContent(sqlElement);
            System.out.println("\n=== 추출된 SQL 내용 ===");
            System.out.println(sqlContent);
            
            // 3. 파라미터 분석 (타입별 구분)
            Map<String, String> parameterInfo = analyzeParametersWithType(sqlContent);
            System.out.println("\n=== 발견된 파라미터 (타입별) ===");
            parameterInfo.forEach((param, type) -> 
                System.out.println(type + "{" + param + "}"));
            
            // 4. 파라미터 파일 생성
            saveParameters(parameterInfo.keySet());
            
            System.out.println("\n=== 준비 완료 ===");
            System.out.println("파라미터 파일: " + PARAMETERS_FILE);
            System.out.println("파일을 편집한 후 MyBatisSimpleExecutor로 실행하세요.");
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * XML 파일을 파싱하여 Document 객체 반환
     */
    private Document parseXmlFile(String xmlFilePath) throws ParserConfigurationException, SAXException, IOException {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(new File(xmlFilePath));
    }
    
    /**
     * 지정된 SQL ID에 해당하는 Element 찾기
     */
    private Element findSqlElement(Document document, String sqlId) {
        NodeList selectNodes = document.getElementsByTagName("select");
        NodeList insertNodes = document.getElementsByTagName("insert");
        NodeList updateNodes = document.getElementsByTagName("update");
        NodeList deleteNodes = document.getElementsByTagName("delete");
        
        // 모든 SQL 태그에서 검색
        NodeList[] allSqlNodes = {selectNodes, insertNodes, updateNodes, deleteNodes};
        
        for (NodeList nodeList : allSqlNodes) {
            for (int i = 0; i < nodeList.getLength(); i++) {
                Element element = (Element) nodeList.item(i);
                if (sqlId.equals(element.getAttribute("id"))) {
                    return element;
                }
            }
        }
        return null;
    }
    
    /**
     * SQL Element에서 텍스트 내용 추출
     */
    private String extractSqlContent(Element sqlElement) {
        StringBuilder sqlBuilder = new StringBuilder();
        extractTextContent(sqlElement, sqlBuilder);
        return sqlBuilder.toString().trim();
    }
    
    /**
     * 재귀적으로 텍스트 내용 추출 (동적 조건 포함)
     */
    private void extractTextContent(Node node, StringBuilder sqlBuilder) {
        if (node.getNodeType() == Node.TEXT_NODE) {
            sqlBuilder.append(node.getTextContent());
        } else if (node.getNodeType() == Node.ELEMENT_NODE) {
            Element element = (Element) node;
            String tagName = element.getTagName();
            
            // 동적 조건 태그 처리
            if ("if".equals(tagName)) {
                sqlBuilder.append("/* IF: ").append(element.getAttribute("test")).append(" */ ");
            } else if ("choose".equals(tagName)) {
                sqlBuilder.append("/* CHOOSE */ ");
            } else if ("when".equals(tagName)) {
                sqlBuilder.append("/* WHEN: ").append(element.getAttribute("test")).append(" */ ");
            } else if ("otherwise".equals(tagName)) {
                sqlBuilder.append("/* OTHERWISE */ ");
            }
            
            // 자식 노드 처리
            NodeList children = node.getChildNodes();
            for (int i = 0; i < children.getLength(); i++) {
                extractTextContent(children.item(i), sqlBuilder);
            }
        }
    }
    
    /**
     * 파라미터 분석 (타입 정보 포함)
     */
    private Map<String, String> analyzeParametersWithType(String sqlContent) {
        Map<String, String> parameterInfo = new LinkedHashMap<>();
        
        // #{paramName} 패턴 찾기 (PreparedStatement 바인딩)
        Pattern hashPattern = Pattern.compile("#\\{([^}]+)\\}");
        Matcher hashMatcher = hashPattern.matcher(sqlContent);
        
        while (hashMatcher.find()) {
            String param = hashMatcher.group(1).trim();
            parameterInfo.put(param, "#");
        }
        
        // ${paramName} 패턴 찾기 (문자열 치환)
        Pattern dollarPattern = Pattern.compile("\\$\\{([^}]+)\\}");
        Matcher dollarMatcher = dollarPattern.matcher(sqlContent);
        
        while (dollarMatcher.find()) {
            String param = dollarMatcher.group(1).trim();
            parameterInfo.put(param, "$");
        }
        
        return parameterInfo;
    }
    
    /**
     * 파라미터를 파일로 저장 (빈 값으로)
     */
    private void saveParameters(Set<String> parameters) throws IOException {
        Properties props = new Properties();
        
        // 헤더 주석 추가
        StringBuilder header = new StringBuilder();
        header.append("# MyBatis 파라미터 설정 파일\n");
        header.append("# 생성일시: ").append(new Date()).append("\n");
        header.append("# 사용법: 각 파라미터에 대해 테스트용 값을 설정하세요.\n");
        header.append("# 빈 값은 null로 처리됩니다.\n\n");
        
        // 파라미터별로 빈 값 설정
        for (String param : parameters) {
            props.setProperty(param, "");
        }
        
        try (FileWriter writer = new FileWriter(PARAMETERS_FILE)) {
            writer.write(header.toString());
            props.store(writer, null);
        }
    }
}
