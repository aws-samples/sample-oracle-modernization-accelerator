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
 * MyBatis XML analysis and test preparation program
 * Find SQL ID from XML file, analyze parameters and generate test files.
 */
public class MyBatisTestPreparator {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: java MyBatisTestPreparator <XML_file_path> <SQL_ID>");
            System.out.println("Example: java MyBatisTestPreparator /home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper/inventory/InventoryMapper.xml selectInventoryStatusAnalysis");
            return;
        }
        
        String xmlFilePath = args[0];
        String sqlId = args[1];
        
        MyBatisTestPreparator preparator = new MyBatisTestPreparator();
        preparator.analyzeAndPrepare(xmlFilePath, sqlId);
    }
    
    public void analyzeAndPrepare(String xmlFilePath, String sqlId) {
        try {
            System.out.println("=== MyBatis XML analysis Started ===");
            System.out.println("XML file: " + xmlFilePath);
            System.out.println("SQL ID: " + sqlId);
            
            // 1. Read XML file and find SQL ID
            Document document = parseXmlFile(xmlFilePath);
            Element sqlElement = findSqlElement(document, sqlId);
            
            if (sqlElement == null) {
                System.err.println("SQL ID '" + sqlId + "' not found.");
                return;
            }
            
            // 2. Extract SQL content
            String sqlContent = extractSqlContent(sqlElement);
            System.out.println("\n=== Extracted SQL Content ===");
            System.out.println(sqlContent);
            
            // 3. Analyze parameters (by type)
            Map<String, String> parameterInfo = analyzeParametersWithType(sqlContent);
            System.out.println("\n=== Found Parameters (by type) ===");
            parameterInfo.forEach((param, type) -> 
                System.out.println(type + "{" + param + "}"));
            
            // 4. Generate parameter file
            saveParameters(parameterInfo.keySet());
            
            System.out.println("\n=== Preparation Completed ===");
            System.out.println("Parameter file: " + PARAMETERS_FILE);
            System.out.println("Edit the file and then run with MyBatisSimpleExecutor.");
            
        } catch (Exception e) {
            System.err.println("Error occurred: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Parse XML file and return Document object
     */
    private Document parseXmlFile(String xmlFilePath) throws ParserConfigurationException, SAXException, IOException {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(new File(xmlFilePath));
    }
    
    /**
     * Find Element corresponding to specified SQL ID
     */
    private Element findSqlElement(Document document, String sqlId) {
        NodeList selectNodes = document.getElementsByTagName("select");
        NodeList insertNodes = document.getElementsByTagName("insert");
        NodeList updateNodes = document.getElementsByTagName("update");
        NodeList deleteNodes = document.getElementsByTagName("delete");
        
        // Search in all SQL tags
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
     * Extract text content from SQL Element
     */
    private String extractSqlContent(Element sqlElement) {
        StringBuilder sqlBuilder = new StringBuilder();
        extractTextContent(sqlElement, sqlBuilder);
        return sqlBuilder.toString().trim();
    }
    
    /**
     * Recursively extract text content (including dynamic conditions)
     */
    private void extractTextContent(Node node, StringBuilder sqlBuilder) {
        if (node.getNodeType() == Node.TEXT_NODE) {
            sqlBuilder.append(node.getTextContent());
        } else if (node.getNodeType() == Node.ELEMENT_NODE) {
            Element element = (Element) node;
            String tagName = element.getTagName();
            
            // Handle dynamic condition tags
            if ("if".equals(tagName)) {
                sqlBuilder.append("/* IF: ").append(element.getAttribute("test")).append(" */ ");
            } else if ("choose".equals(tagName)) {
                sqlBuilder.append("/* CHOOSE */ ");
            } else if ("when".equals(tagName)) {
                sqlBuilder.append("/* WHEN: ").append(element.getAttribute("test")).append(" */ ");
            } else if ("otherwise".equals(tagName)) {
                sqlBuilder.append("/* OTHERWISE */ ");
            }
            
            // Process child nodes
            NodeList children = node.getChildNodes();
            for (int i = 0; i < children.getLength(); i++) {
                extractTextContent(children.item(i), sqlBuilder);
            }
        }
    }
    
    /**
     * Analyze parameters (including type information)
     */
    private Map<String, String> analyzeParametersWithType(String sqlContent) {
        Map<String, String> parameterInfo = new LinkedHashMap<>();
        
        // Find #{paramName} pattern (PreparedStatement binding)
        Pattern hashPattern = Pattern.compile("#\\{([^}]+)\\}");
        Matcher hashMatcher = hashPattern.matcher(sqlContent);
        
        while (hashMatcher.find()) {
            String param = hashMatcher.group(1).trim();
            parameterInfo.put(param, "#");
        }
        
        // Find ${paramName} pattern (string substitution)
        Pattern dollarPattern = Pattern.compile("\\$\\{([^}]+)\\}");
        Matcher dollarMatcher = dollarPattern.matcher(sqlContent);
        
        while (dollarMatcher.find()) {
            String param = dollarMatcher.group(1).trim();
            parameterInfo.put(param, "$");
        }
        
        return parameterInfo;
    }
    
    /**
     * Save parameters to file (with empty values)
     */
    private void saveParameters(Set<String> parameters) throws IOException {
        Properties props = new Properties();
        
        // Add header comments
        StringBuilder header = new StringBuilder();
        header.append("# MyBatis parameter configuration file\n");
        header.append("# Generated: ").append(new Date()).append("\n");
        header.append("# Usage: Set test values for each parameter.\n");
        header.append("# Empty values are treated as null.\n\n");
        
        // Set empty values for each parameter
        for (String param : parameters) {
            props.setProperty(param, "");
        }
        
        try (FileWriter writer = new FileWriter(PARAMETERS_FILE)) {
            writer.write(header.toString());
            props.store(writer, null);
        }
    }
}
