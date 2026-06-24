package com.oma.validator;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * Extracts SQL IDs from MyBatis mapper XML files
 */
public class SqlIdExtractor {

    /**
     * Extract all SQL IDs from a mapper XML file
     *
     * @param mapperFile Path to mapper XML file
     * @return List of SQL IDs in format "namespace.id"
     * @throws Exception if parsing fails
     */
    public static List<String> extractSqlIds(File mapperFile) throws Exception {
        List<String> sqlIds = new ArrayList<>();

        // Parse XML
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(mapperFile);

        // Get namespace
        Element root = doc.getDocumentElement();
        String namespace = root.getAttribute("namespace");

        if (namespace == null || namespace.isEmpty()) {
            throw new Exception("Mapper XML missing namespace attribute: " + mapperFile.getName());
        }

        // Extract IDs from select, insert, update, delete elements
        extractIds(doc, "select", namespace, sqlIds);
        extractIds(doc, "insert", namespace, sqlIds);
        extractIds(doc, "update", namespace, sqlIds);
        extractIds(doc, "delete", namespace, sqlIds);

        return sqlIds;
    }

    /**
     * Extract all SQL IDs from mapper files in a directory
     *
     * @param mapperDir Directory containing mapper XML files
     * @return List of SQL IDs in format "namespace.id"
     * @throws Exception if parsing fails
     */
    public static List<String> extractSqlIds(String mapperDir) throws Exception {
        List<String> allSqlIds = new ArrayList<>();
        File directory = new File(mapperDir);

        if (!directory.exists() || !directory.isDirectory()) {
            throw new Exception("Invalid mapper directory: " + mapperDir);
        }

        // Recursively process all XML files
        processDirectory(directory, allSqlIds);

        return allSqlIds;
    }

    private static void processDirectory(File directory, List<String> sqlIds) throws Exception {
        File[] files = directory.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    processDirectory(file, sqlIds);
                } else if (file.getName().endsWith(".xml")) {
                    try {
                        List<String> fileSqlIds = extractSqlIds(file);
                        sqlIds.addAll(fileSqlIds);
                    } catch (Exception e) {
                        System.err.println("Warning: Failed to parse " + file.getName() + ": " + e.getMessage());
                    }
                }
            }
        }
    }

    private static void extractIds(Document doc, String tagName, String namespace, List<String> sqlIds) {
        NodeList nodes = doc.getElementsByTagName(tagName);
        for (int i = 0; i < nodes.getLength(); i++) {
            Element element = (Element) nodes.item(i);
            String id = element.getAttribute("id");

            if (id != null && !id.isEmpty()) {
                // Create fully qualified SQL ID
                String fullId = namespace + "." + id;
                sqlIds.add(fullId);
            }
        }
    }

    /**
     * Main method for testing
     */
    public static void main(String[] args) {
        if (args.length != 1) {
            System.out.println("Usage: java SqlIdExtractor <mapper-dir>");
            System.exit(1);
        }

        try {
            String mapperDir = args[0];
            System.out.println("Extracting SQL IDs from: " + mapperDir);
            System.out.println();

            List<String> sqlIds = extractSqlIds(mapperDir);

            System.out.println("Found " + sqlIds.size() + " SQL IDs:");
            for (String sqlId : sqlIds) {
                System.out.println("  - " + sqlId);
            }

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
