package com.example;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springaicommunity.mcp.annotation.McpTool;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.regions.Region;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class OmaMcpTools {

    private static final Logger logger = LoggerFactory.getLogger(OmaMcpTools.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @Value("${mma.sc.default.s3path}")
    private String defaultS3Path;
    
    private String getS3Path(String s3Path) {
        if (s3Path == null || s3Path.trim().isEmpty() || s3Path.equalsIgnoreCase("default")) {
            logger.info("Using default S3 path: {}", defaultS3Path);
            return defaultS3Path;
        }
        return s3Path;
    }
    
    private S3Client createS3Client(String bucket) {
        try {
            // Try to get bucket region
            S3Client tempClient = S3Client.builder()
                .region(Region.US_EAST_1)
                .build();
            
            HeadBucketResponse response = tempClient.headBucket(HeadBucketRequest.builder()
                .bucket(bucket)
                .build());
            
            String regionStr = response.sdkHttpResponse().firstMatchingHeader("x-amz-bucket-region")
                .orElse("us-east-1");
            
            tempClient.close();
            
            return S3Client.builder()
                .region(Region.of(regionStr))
                .build();
        } catch (Exception e) {
            // Fallback to cross-region client
            return S3Client.builder()
                .crossRegionAccessEnabled(true)
                .build();
        }
    }

    @McpTool(name = "analyze_dms_sc_project", description = "Analyze DMS Schema Conversion project from S3 path and extract metadata, mappings, and DDL scripts")
    public Map<String, Object> analyzeDmsScProject(String s3Path) {
        s3Path = getS3Path(s3Path);
        logger.info("Analyzing DMS SC project from: {}", s3Path);
        Map<String, Object> result = new HashMap<>();
        S3Client s3Client = null;
        
        try {
            Path localBase = getLocalPathFromS3(s3Path);
            
            // Check if already analyzed
            Path analysisFile = localBase.resolve("analysis_results.json");
            if (Files.exists(analysisFile)) {
                logger.info("Loading existing analysis from: {}", analysisFile);
                return loadAnalysisResults(localBase);
            }
            
            String[] parts = s3Path.replace("s3://", "").split("/", 2);
            String bucket = parts[0];
            String prefix = parts.length > 1 ? parts[1].replaceAll("/$", "") : "";
            
            s3Client = createS3Client(bucket);
            
            String projectId = UUID.randomUUID().toString();
            Files.createDirectories(localBase);
            
            List<S3Object> objects = listS3Objects(s3Client, bucket, prefix);
            List<Map<String, Object>> fileMetadata = new ArrayList<>();
            
            for (S3Object obj : objects) {
                if (obj.key().endsWith("/")) continue;
                
                String content = getS3ObjectContent(s3Client, bucket, obj.key());
                JsonNode json = objectMapper.readTree(content);
                
                Path localFile = localBase.resolve(obj.key().replace(prefix, "").replaceFirst("^/", ""));
                Files.createDirectories(localFile.getParent());
                Files.writeString(localFile, content);
                
                fileMetadata.add(Map.of(
                    "file_path", obj.key(),
                    "local_path", localFile.toString(),
                    "size", obj.size()
                ));
            }
            
            Map<String, Object> analysis = performAnalysis(localBase, projectId);
            
            result.put("success", true);
            result.put("project_id", projectId);
            result.put("local_base", localBase.toString());
            result.put("files_processed", fileMetadata.size());
            result.putAll(analysis);
            
        } catch (Exception e) {
            logger.error("Analysis failed: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("error", e.getMessage());
        } finally {
            if (s3Client != null) {
                s3Client.close();
            }
        }
        
        return result;
    }

    @McpTool(name = "report_dms_sc_project", description = "Get analysis report with optional filters: objectType, schemaName, objectName (all case-insensitive)")
    public Map<String, Object> reportDmsScProject(String s3Path, String objectType, String schemaName, String objectName) {
        s3Path = getS3Path(s3Path);
        logger.info("Loading report for: {} (type={}, schema={}, name={})", s3Path, objectType, schemaName, objectName);
        Map<String, Object> result = new HashMap<>();
        
        try {
            Path localBase = getLocalPathFromS3(s3Path);
            Path analysisFile = localBase.resolve("analysis_results.json");
            
            if (!Files.exists(analysisFile)) {
                result.put("success", false);
                result.put("error", "No analysis found. Please run analyze_dms_sc_project first.");
                result.put("s3_path", s3Path);
                result.put("expected_file", analysisFile.toString());
                return result;
            }
            
            Map<String, Object> analysis = loadAnalysisResults(localBase);
            
            // Apply filters if provided
            if (objectType != null && !objectType.isEmpty()) {
                analysis = filterByObjectType(analysis, objectType.toLowerCase());
            }
            if (schemaName != null && !schemaName.isEmpty()) {
                analysis = filterBySchema(analysis, schemaName.toLowerCase());
            }
            if (objectName != null && !objectName.isEmpty()) {
                analysis = filterByObjectName(analysis, objectName.toLowerCase());
            }
            
            return analysis;
            
        } catch (Exception e) {
            logger.error("Failed to load report: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }
    
    private Map<String, Object> filterByObjectType(Map<String, Object> analysis, String objectType) {
        Map<String, Object> filtered = new HashMap<>();
        filtered.put("success", analysis.get("success"));
        filtered.put("local_base", analysis.get("local_base"));
        filtered.put("analysis_file", analysis.get("analysis_file"));
        
        String mappingKey = objectType + "_mappings";
        if (analysis.containsKey(mappingKey)) {
            filtered.put(mappingKey, analysis.get(mappingKey));
        } else {
            // Try to find matching key
            for (String key : analysis.keySet()) {
                if (key.toLowerCase().contains(objectType) && key.endsWith("_mappings")) {
                    filtered.put(key, analysis.get(key));
                    break;
                }
            }
        }
        
        return filtered;
    }
    
    private Map<String, Object> filterBySchema(Map<String, Object> analysis, String schemaName) {
        Map<String, Object> filtered = new HashMap<>();
        filtered.put("success", analysis.get("success"));
        filtered.put("local_base", analysis.get("local_base"));
        filtered.put("analysis_file", analysis.get("analysis_file"));
        
        for (Map.Entry<String, Object> entry : analysis.entrySet()) {
            if (entry.getKey().endsWith("_mappings") && entry.getValue() instanceof List) {
                List<Map<String, Object>> mappings = (List<Map<String, Object>>) entry.getValue();
                List<Map<String, Object>> filteredMappings = mappings.stream()
                    .filter(m -> {
                        String srcSchema = (String) m.get("src_schema");
                        return srcSchema != null && srcSchema.toLowerCase().equals(schemaName);
                    })
                    .collect(Collectors.toList());
                
                if (!filteredMappings.isEmpty()) {
                    filtered.put(entry.getKey(), filteredMappings);
                }
            }
        }
        
        return filtered;
    }
    
    private Map<String, Object> filterByObjectName(Map<String, Object> analysis, String objectName) {
        Map<String, Object> filtered = new HashMap<>();
        filtered.put("success", analysis.get("success"));
        filtered.put("local_base", analysis.get("local_base"));
        filtered.put("analysis_file", analysis.get("analysis_file"));
        
        for (Map.Entry<String, Object> entry : analysis.entrySet()) {
            if (entry.getKey().endsWith("_mappings") && entry.getValue() instanceof List) {
                List<Map<String, Object>> mappings = (List<Map<String, Object>>) entry.getValue();
                List<Map<String, Object>> filteredMappings = mappings.stream()
                    .filter(m -> {
                        String srcName = (String) m.get("src_name");
                        return srcName != null && srcName.toLowerCase().equals(objectName);
                    })
                    .collect(Collectors.toList());
                
                if (!filteredMappings.isEmpty()) {
                    filtered.put(entry.getKey(), filteredMappings);
                }
            }
        }
        
        return filtered;
    }

    @McpTool(name = "cleanup_local_cache", description = "Clean up local cache for DMS SC project using S3 path")
    public Map<String, Object> cleanupLocalCache(String s3Path) {
        s3Path = getS3Path(s3Path);
        logger.info("Cleaning up cache for: {}", s3Path);
        Map<String, Object> result = new HashMap<>();
        
        try {
            Path targetPath;
            if (s3Path == null || s3Path.isEmpty()) {
                targetPath = Paths.get(System.getProperty("user.home"), ".mma-sc");
            } else {
                targetPath = getLocalPathFromS3(s3Path);
            }
            
            if (!Files.exists(targetPath)) {
                result.put("success", true);
                result.put("message", "Path does not exist");
                result.put("path", targetPath.toString());
                return result;
            }
            
            long deletedCount = Files.walk(targetPath)
                .sorted(Comparator.reverseOrder())
                .peek(p -> {
                    try { Files.delete(p); } catch (IOException e) {}
                })
                .count();
            
            result.put("success", true);
            result.put("deleted_items", deletedCount);
            result.put("path", targetPath.toString());
            result.put("s3_path", s3Path);
            
        } catch (Exception e) {
            logger.error("Cleanup failed: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }
    
    private Path getLocalPathFromS3(String s3Path) {
        String[] parts = s3Path.replace("s3://", "").split("/", 2);
        String bucket = parts[0];
        String prefix = parts.length > 1 ? parts[1].replaceAll("/$", "") : "";
        String sanitizedPrefix = prefix.replaceAll("/", "_");
        if (sanitizedPrefix.isEmpty()) sanitizedPrefix = "root";
        return Paths.get(System.getProperty("user.home"), ".mma-sc", bucket, sanitizedPrefix);
    }
    
    private Map<String, Object> loadAnalysisResults(Path localBase) throws IOException {
        Path analysisFile = localBase.resolve("analysis_results.json");
        Map<String, Object> analysis = objectMapper.readValue(analysisFile.toFile(), Map.class);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("local_base", localBase.toString());
        result.put("analysis_file", analysisFile.toString());
        result.putAll(analysis);
        
        return result;
    }

    private List<S3Object> listS3Objects(S3Client s3Client, String bucket, String prefix) {
        List<S3Object> objects = new ArrayList<>();
        ListObjectsV2Request request = ListObjectsV2Request.builder()
            .bucket(bucket)
            .prefix(prefix)
            .build();
        
        ListObjectsV2Response response;
        do {
            response = s3Client.listObjectsV2(request);
            objects.addAll(response.contents());
            request = request.toBuilder().continuationToken(response.nextContinuationToken()).build();
        } while (response.isTruncated());
        
        return objects;
    }

    private String getS3ObjectContent(S3Client s3Client, String bucket, String key) throws IOException {
        return s3Client.getObjectAsBytes(GetObjectRequest.builder()
            .bucket(bucket)
            .key(key)
            .build()).asUtf8String();
    }

    private Map<String, Object> performAnalysis(Path basePath, String projectId) throws IOException {
        Map<String, Object> analysis = new HashMap<>();
        
        analysis.put("servers", extractServerDetails(basePath));
        analysis.put("table_mappings", extractTableMappings(basePath));
        analysis.put("view_mappings", extractObjectMappings(basePath, "view", "Views"));
        analysis.put("mview_mappings", extractObjectMappings(basePath, "materialized-view", "!22Materialized!20Views!22"));
        analysis.put("function_mappings", extractObjectMappings(basePath, "function", "Functions"));
        analysis.put("procedure_mappings", extractObjectMappings(basePath, "procedure", "Procedures"));
        analysis.put("synonym_mappings", extractObjectMappings(basePath, "synonym", "Synonyms"));
        analysis.put("pkg_procedure_mappings", extractPkgProcedureMappings(basePath));
        analysis.put("pkg_function_mappings", extractPkgFunctionMappings(basePath));
        
        extractAndSaveDDLs(basePath);
        
        // Save analysis results to JSON file
        Path analysisFile = basePath.resolve("analysis_results.json");
        objectMapper.writerWithDefaultPrettyPrinter().writeValue(analysisFile.toFile(), analysis);
        logger.info("Analysis results saved to: {}", analysisFile);
        
        return analysis;
    }
    
    private List<Map<String, Object>> extractObjectMappings(Path basePath, String objectType, String category) throws IOException {
        Map<String, Map<String, Object>> sourceObjects = new HashMap<>();
        Map<String, Map<String, Object>> targetObjects = new HashMap<>();
        
        Files.walk(basePath)
            .filter(Files::isRegularFile)
            .filter(p -> {
                String name = p.getFileName().toString();
                return name.contains("." + category + ".") && p.toString().contains("/s-");
            })
            .forEach(p -> loadObjectFile(p, sourceObjects, objectType));
        
        Files.walk(basePath)
            .filter(Files::isRegularFile)
            .filter(p -> {
                String name = p.getFileName().toString();
                return name.contains("." + category + ".") && p.toString().contains("/t-");
            })
            .forEach(p -> loadObjectFile(p, targetObjects, objectType));
        
        return matchObjectMappings(sourceObjects, targetObjects);
    }
    
    private void loadObjectFile(Path file, Map<String, Map<String, Object>> map, String expectedType) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode obj = json.at("/content/0");
            String type = obj.path("type").asText();
            
            if (expectedType.equals(type) || type.contains(expectedType)) {
                String name = obj.path("name").asText();
                boolean isSource = file.toString().contains("/s-");
                String key;
                
                if (isSource) {
                    key = obj.at("/synchronization_object/name").asText();
                } else {
                    key = obj.path("id").asText();
                }
                
                if (!key.isEmpty()) {
                    Map<String, Object> objInfo = new HashMap<>();
                    objInfo.put("schema", obj.at("/locator/schema-name").asText());
                    objInfo.put("name", name);
                    objInfo.put("file", file);
                    map.put(key, objInfo);
                    logger.debug("Loaded {}: {} -> {} ({})", expectedType, name, key, isSource ? "source" : "target");
                } else {
                    // No target mapping - add with NULL target
                    if (isSource) {
                        Map<String, Object> objInfo = new HashMap<>();
                        objInfo.put("schema", obj.at("/locator/schema-name").asText());
                        objInfo.put("name", name);
                        objInfo.put("file", file);
                        objInfo.put("no_target", true);
                        map.put("NO_TARGET_" + name, objInfo);
                        logger.debug("Loaded {} without target: {}", expectedType, name);
                    }
                }
            }
        } catch (Exception e) {
            logger.debug("Failed to load object file: {}", file, e);
        }
    }
    
    private List<Map<String, Object>> matchObjectMappings(Map<String, Map<String, Object>> source, Map<String, Map<String, Object>> target) {
        List<Map<String, Object>> mappings = new ArrayList<>();
        
        // Matched objects
        source.entrySet().stream()
            .filter(e -> !e.getKey().startsWith("NO_TARGET_"))
            .filter(e -> target.containsKey(e.getKey()))
            .forEach(e -> {
                Map<String, Object> src = e.getValue();
                Map<String, Object> trg = target.get(e.getKey());
                Map<String, Object> mapping = new HashMap<>();
                mapping.put("src_schema", src.get("schema"));
                mapping.put("src_name", src.get("name"));
                mapping.put("trg_schema", trg.get("schema"));
                mapping.put("trg_name", trg.get("name"));
                mappings.add(mapping);
            });
        
        // Objects without target
        source.entrySet().stream()
            .filter(e -> e.getKey().startsWith("NO_TARGET_") || !target.containsKey(e.getKey()))
            .forEach(e -> {
                Map<String, Object> src = e.getValue();
                Map<String, Object> mapping = new HashMap<>();
                mapping.put("src_schema", src.get("schema"));
                mapping.put("src_name", src.get("name"));
                mapping.put("trg_schema", null);
                mapping.put("trg_name", null);
                mappings.add(mapping);
            });
        
        return mappings;
    }

    private List<Map<String, Object>> extractServerDetails(Path basePath) throws IOException {
        return Files.walk(basePath)
            .filter(p -> p.toString().matches(".*[/\\\\][st]-server$"))
            .map(this::parseServerFile)
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
    }

    private Map<String, Object> parseServerFile(Path file) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode server = json.at("/content/0/children/0");
            return Map.of(
                "server_type", file.toString().contains("/t-server") ? "target" : "source",
                "server_name", server.path("name").asText(),
                "vendor", server.at("/server_info/vendorName").asText(),
                "engine", server.at("/server_info/vendorEngine").asText(),
                "version", server.at("/server_info/vendorEngineVersion").asText()
            );
        } catch (Exception e) {
            return null;
        }
    }

    private List<Map<String, Object>> extractTableMappings(Path basePath) throws IOException {
        Map<String, Map<String, Object>> sourceTables = new HashMap<>();
        Map<String, Map<String, Object>> targetTables = new HashMap<>();
        
        Files.walk(basePath)
            .filter(Files::isRegularFile)
            .filter(p -> {
                String name = p.getFileName().toString();
                return name.matches("Schemas\\.[^.]+\\.Tables\\.[^.]+$") && 
                       p.toString().contains("/s-");
            })
            .forEach(p -> loadTableFile(p, sourceTables));
        
        Files.walk(basePath)
            .filter(Files::isRegularFile)
            .filter(p -> {
                String name = p.getFileName().toString();
                return name.matches("Schemas\\.[^.]+\\.Tables\\.[^.]+$") && 
                       p.toString().contains("/t-");
            })
            .forEach(p -> loadTableFile(p, targetTables));
        
        return matchTableMappings(sourceTables, targetTables);
    }
    
    private void loadTableFile(Path file, Map<String, Map<String, Object>> map) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode table = json.at("/content/0");
            if ("table".equals(table.path("type").asText())) {
                String tableName = table.path("name").asText();
                if (!tableName.startsWith("DR$")) {
                    boolean isSource = file.toString().contains("/s-");
                    String key;
                    if (isSource) {
                        // Source: use synchronization_object.name as key
                        key = table.at("/synchronization_object/name").asText();
                    } else {
                        // Target: use id as key
                        key = table.path("id").asText();
                    }
                    
                    if (!key.isEmpty()) {
                        Map<String, Object> tableInfo = new HashMap<>();
                        tableInfo.put("schema", table.at("/locator/schema-name").asText());
                        tableInfo.put("name", tableName);
                        tableInfo.put("file", file);
                        map.put(key, tableInfo);
                        logger.debug("Loaded table: {} -> {} ({})", tableName, key, isSource ? "source" : "target");
                    }
                }
            }
        } catch (Exception e) {
            logger.debug("Failed to load table file: {}", file, e);
        }
    }
    
    private List<Map<String, Object>> matchTableMappings(Map<String, Map<String, Object>> source, Map<String, Map<String, Object>> target) {
        return source.entrySet().stream()
            .filter(e -> target.containsKey(e.getKey()))
            .map(e -> {
                Map<String, Object> src = e.getValue();
                Map<String, Object> trg = target.get(e.getKey());
                Map<String, Object> mapping = new HashMap<>();
                mapping.put("src_schema", src.get("schema"));
                mapping.put("src_name", src.get("name"));
                mapping.put("trg_schema", trg.get("schema"));
                mapping.put("trg_name", trg.get("name"));
                return mapping;
            })
            .collect(Collectors.toList());
    }

    private List<Map<String, Object>> extractPkgProcedureMappings(Path basePath) throws IOException {
        return Files.walk(basePath)
            .filter(p -> p.toString().contains("/s-") && p.toString().contains(".Packages.") && 
                        p.toString().contains("!22Public!20procedures!"))
            .map(this::parsePkgObject)
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
    }

    private List<Map<String, Object>> extractPkgFunctionMappings(Path basePath) throws IOException {
        return Files.walk(basePath)
            .filter(p -> p.toString().contains("/s-") && p.toString().contains(".Packages.") && 
                        p.toString().contains("!22Public!20functions!"))
            .map(this::parsePkgObject)
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
    }

    private Map<String, Object> parsePkgObject(Path file) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode content = json.at("/content/0");
            String relatedName = content.at("/related_converted_objects/0/name").asText();
            String[] parts = relatedName.split("\\.");
            
            return Map.of(
                "src_schema", content.at("/locator/schema-name").asText(),
                "src_package", content.at("/locator/package-name").asText(),
                "src_name", content.path("name").asText(),
                "trg_schema", parts.length > 1 ? parts[1] : "",
                "trg_name", parts.length > 3 ? parts[3] : ""
            );
        } catch (Exception e) {
            return null;
        }
    }

    private void extractAndSaveDDLs(Path basePath) throws IOException {
        Path sourceDdlDir = basePath.resolve("ddl/source");
        Path targetDdlDir = basePath.resolve("ddl/target");
        Files.createDirectories(sourceDdlDir);
        Files.createDirectories(targetDdlDir);
        
        Files.walk(basePath)
            .filter(p -> p.toString().endsWith(".json") || p.toString().matches(".*[^.]+$"))
            .forEach(p -> extractDDL(p, sourceDdlDir, targetDdlDir));
    }

    private void extractDDL(Path file, Path sourceDdlDir, Path targetDdlDir) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode content = json.at("/content/0");
            
            // Try multiple fields for DDL
            String ddl = content.path("sql").asText("");
            if (ddl.isEmpty() || "null".equalsIgnoreCase(ddl)) {
                ddl = content.path("ddl").asText("");
            }
            if (ddl.isEmpty() || "null".equalsIgnoreCase(ddl)) {
                ddl = content.path("definition").asText("");
            }
            
            // Skip if still empty or null
            if (ddl.isEmpty() || "null".equalsIgnoreCase(ddl)) {
                return;
            }
            
            String schema = content.at("/locator/schema-name").asText("");
            String name = content.path("name").asText("");
            String type = content.path("type").asText("");
            
            if (schema.isEmpty() || name.isEmpty()) return;
            
            boolean isSource = file.toString().contains("/s-");
            Path ddlDir = isSource ? sourceDdlDir : targetDdlDir;
            String filename = String.format("%s_%s_%s.sql", schema, type, name).replaceAll("[^a-zA-Z0-9_.-]", "_");
            
            Files.writeString(ddlDir.resolve(filename), ddl);
        } catch (Exception e) {
            logger.debug("Failed to extract DDL from: {}", file, e);
        }
    }

    @McpTool(name = "get_offline_ddl", description = "Retrieve offline DDL for a specific object. Parameters: s3Path, ddlType (source/target), schemaName, objectType, objectName")
    public Map<String, Object> getOfflineDdl(String s3Path, String ddlType, String schemaName, String objectType, String objectName) {
        s3Path = getS3Path(s3Path);
        logger.info("Retrieving DDL: {} {} {}.{}.{}", s3Path, ddlType, schemaName, objectType, objectName);
        Map<String, Object> result = new HashMap<>();
        
        try {
            Path localBase = getLocalPathFromS3(s3Path);
            Path ddlDir = localBase.resolve("ddl/" + (ddlType != null && ddlType.equalsIgnoreCase("source") ? "source" : "target"));
            
            if (!Files.exists(ddlDir)) {
                result.put("success", false);
                result.put("error", "DDL directory not found. Run analyze_dms_sc_project first.");
                return result;
            }
            
            String pattern = String.format("%s_%s_%s.sql", 
                schemaName != null ? schemaName : "*",
                objectType != null ? objectType : "*", 
                objectName != null ? objectName : "*"
            ).replaceAll("[^a-zA-Z0-9_.*-]", "_");
            
            List<Map<String, String>> ddls = new ArrayList<>();
            Files.walk(ddlDir, 1)
                .filter(Files::isRegularFile)
                .filter(p -> matchesPattern(p.getFileName().toString(), pattern))
                .forEach(p -> {
                    try {
                        Map<String, String> ddlInfo = new HashMap<>();
                        ddlInfo.put("filename", p.getFileName().toString());
                        ddlInfo.put("ddl", Files.readString(p));
                        ddls.add(ddlInfo);
                    } catch (IOException e) {
                        logger.error("Failed to read DDL file: {}", p, e);
                    }
                });
            
            result.put("success", true);
            result.put("count", ddls.size());
            result.put("ddls", ddls);
            
        } catch (Exception e) {
            logger.error("Failed to retrieve DDL", e);
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }
    
    private boolean matchesPattern(String filename, String pattern) {
        String regex = pattern.replace("*", ".*");
        return filename.matches(regex);
    }
}
