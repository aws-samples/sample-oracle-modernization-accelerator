package com.example;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springaicommunity.mcp.annotation.McpTool;
import software.amazon.awssdk.core.ResponseBytes;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.regions.Region;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class OmaScMcpTools {

    private static final Logger logger = LoggerFactory.getLogger(OmaScMcpTools.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @Value("${oma.sc.default.s3path:}")
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
            S3Client tempClient = S3Client.builder().region(Region.US_EAST_1).build();
            HeadBucketResponse response = tempClient.headBucket(HeadBucketRequest.builder().bucket(bucket).build());
            String regionStr = response.sdkHttpResponse().firstMatchingHeader("x-amz-bucket-region").orElse("us-east-1");
            tempClient.close();
            return S3Client.builder().region(Region.of(regionStr)).build();
        } catch (Exception e) {
            return S3Client.builder().crossRegionAccessEnabled(true).build();
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
            
            // Check if it's a ZIP file
            if (prefix.endsWith(".zip")) {
                logger.info("Detected ZIP file, downloading and extracting: {}", prefix);
                byte[] zipBytes = s3Client.getObjectAsBytes(
                    GetObjectRequest.builder().bucket(bucket).key(prefix).build()
                ).asByteArray();
                
                Path zipFile = localBase.resolve("project.zip");
                Files.write(zipFile, zipBytes);
                
                // Extract ZIP
                try (java.util.zip.ZipInputStream zis = new java.util.zip.ZipInputStream(
                        new java.io.ByteArrayInputStream(zipBytes))) {
                    java.util.zip.ZipEntry entry;
                    while ((entry = zis.getNextEntry()) != null) {
                        if (entry.isDirectory()) continue;
                        Path targetFile = localBase.resolve(entry.getName());
                        Files.createDirectories(targetFile.getParent());
                        Files.copy(zis, targetFile, StandardCopyOption.REPLACE_EXISTING);
                    }
                }
                logger.info("ZIP file extracted to: {}", localBase);
                
                // Also download DDL files from s-* directories
                String projectPrefix = prefix.substring(0, prefix.lastIndexOf('/') + 1);
                logger.info("Downloading DDL files from: {}", projectPrefix);
                List<S3Object> ddlObjects = listS3Objects(s3Client, bucket, projectPrefix + "s-");
                for (S3Object obj : ddlObjects) {
                    if (obj.key().endsWith("/")) continue;
                    String content = getS3ObjectContent(s3Client, bucket, obj.key());
                    Path localFile = localBase.resolve(obj.key().replace(projectPrefix, ""));
                    Files.createDirectories(localFile.getParent());
                    Files.writeString(localFile, content, java.nio.charset.StandardCharsets.UTF_8);
                }
                logger.info("Downloaded {} DDL files", ddlObjects.size());
            } else {
                // Original directory-based logic
                List<S3Object> objects = listS3Objects(s3Client, bucket, prefix);
                List<Map<String, Object>> fileMetadata = new ArrayList<>();
                
                for (S3Object obj : objects) {
                    if (obj.key().endsWith("/")) continue;
                    String content = getS3ObjectContent(s3Client, bucket, obj.key());
                    Path localFile = localBase.resolve(obj.key().replace(prefix, "").replaceFirst("^/", ""));
                    Files.createDirectories(localFile.getParent());
                    Files.writeString(localFile, content, java.nio.charset.StandardCharsets.UTF_8);
                    fileMetadata.add(Map.of("file_path", obj.key(), "local_path", localFile.toString(), "size", obj.size()));
                }
            }
            
            Map<String, Object> analysis = performAnalysis(localBase, projectId);
            result.put("success", true);
            result.put("project_id", projectId);
            result.put("local_base", localBase.toString());
            result.putAll(analysis);
            
        } catch (Exception e) {
            logger.error("Analysis failed: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("error", e.getMessage());
        } finally {
            if (s3Client != null) s3Client.close();
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
                return result;
            }
            
            Map<String, Object> analysis = loadAnalysisResults(localBase);
            
            if (objectType != null && !objectType.isEmpty()) analysis = filterByObjectType(analysis, objectType.toLowerCase());
            if (schemaName != null && !schemaName.isEmpty()) analysis = filterBySchema(analysis, schemaName.toLowerCase());
            if (objectName != null && !objectName.isEmpty()) analysis = filterByObjectName(analysis, objectName.toLowerCase());
            
            return analysis;
            
        } catch (Exception e) {
            logger.error("Failed to load report: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }

    @McpTool(name = "get_offline_ddl", description = "Retrieve offline DDL for a specific object. Parameters: s3Path, ddlType (source/target), schemaName, objectType, objectName")
    public Map<String, Object> getOfflineDdl(String s3Path, String ddlType, String schemaName, String objectType, String objectName) {
        s3Path = getS3Path(s3Path);
        logger.info("Retrieving DDL: {} {} {}.{}.{}", s3Path, ddlType, schemaName, objectType, objectName);
        Map<String, Object> result = new HashMap<>();
        
        try {
            Path localBase = getLocalPathFromS3(s3Path);
            Path ddlDir = localBase.resolve("ddl/source");
            
            logger.info("Looking for DDL in: {}", ddlDir);
            logger.info("Directory exists: {}", Files.exists(ddlDir));
            
            if (!Files.exists(ddlDir)) {
                result.put("success", false);
                result.put("error", "DDL directory not found");
                return result;
            }
            
            List<Map<String, String>> ddls = new ArrayList<>();
            long fileCount = Files.walk(ddlDir, 1)
                .filter(Files::isRegularFile)
                .filter(p -> p.toString().endsWith(".sql"))
                .count();
            
            logger.info("Found {} SQL files in directory", fileCount);
            
            Files.walk(ddlDir, 1)
                .filter(Files::isRegularFile)
                .filter(p -> p.toString().endsWith(".sql"))
                .forEach(p -> {
                    try {
                        String filename = p.getFileName().toString();
                        String filenameLower = filename.toLowerCase();
                        
                        boolean matches = true;
                        if (schemaName != null && !schemaName.isEmpty()) {
                            if (!filenameLower.startsWith(schemaName.toLowerCase() + "_")) {
                                matches = false;
                            }
                        }
                        if (objectName != null && !objectName.isEmpty()) {
                            if (!filenameLower.contains(objectName.toLowerCase())) {
                                matches = false;
                            }
                        }
                        
                        if (matches) {
                            String sql = Files.readString(p);
                            ddls.add(Map.of("filename", filename, "ddl", sql));
                            logger.info("Found DDL: {} (length: {})", filename, sql.length());
                        } else {
                            logger.info("Skipped: {} (schema={}, object={})", filename, schemaName, objectName);
                        }
                    } catch (IOException e) {
                        logger.error("Failed to read DDL file: {}", p, e);
                    }
                });
            
            result.put("success", true);
            result.put("count", ddls.size());
            result.put("ddls", ddls);
            
        } catch (Exception e) {
            logger.error("Failed to retrieve DDL: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }

    @McpTool(name = "convert_ddl_to_pg", description = "Convert Oracle DDL to PostgreSQL using Bedrock Claude. Parameters: oracleDdl, objectType, complexity")
    public Map<String, Object> convertDdlToPg(String oracleDdl, String objectType, String complexity) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            String prompt = String.format("""
                Convert this Oracle DDL to PostgreSQL-compatible DDL.
                
                Object Type: %s
                Complexity: %s
                
                Oracle DDL:
                %s
                
                Requirements:
                - Follow Aurora PostgreSQL best practices
                - Convert PL/SQL to PL/pgSQL
                - Map Oracle types to PostgreSQL types (VARCHAR2→VARCHAR, NUMBER→NUMERIC, DATE→TIMESTAMP)
                - Convert built-ins (SYSDATE→CURRENT_TIMESTAMP, NVL→COALESCE, DECODE→CASE)
                - Preserve business logic exactly
                - For procedures, convert to functions returning VOID
                - For packages, create standalone functions
                
                Return ONLY the PostgreSQL DDL, no explanations.
                """, objectType, complexity, oracleDdl);
            
            Map<String, Object> requestBody = Map.of(
                "anthropic_version", "bedrock-2023-05-31",
                "max_tokens", 4096,
                "messages", List.of(Map.of("role", "user", "content", prompt))
            );
            
            String requestJson = objectMapper.writeValueAsString(requestBody);
            
            try (BedrockRuntimeClient bedrockClient = BedrockRuntimeClient.builder()
                    .region(Region.US_EAST_1)
                    .build()) {
                
                InvokeModelRequest request = InvokeModelRequest.builder()
                    .modelId("us.anthropic.claude-3-5-sonnet-20241022-v2:0")
                    .body(SdkBytes.fromUtf8String(requestJson))
                    .build();
                
                InvokeModelResponse response = bedrockClient.invokeModel(request);
                String responseBody = response.body().asUtf8String();
                
                JsonNode responseJson = objectMapper.readTree(responseBody);
                String pgDdl = responseJson.get("content").get(0).get("text").asText();
                
                result.put("success", true);
                result.put("postgresql_ddl", pgDdl);
                result.put("object_type", objectType);
                result.put("complexity", complexity);
            }
            
        } catch (Exception e) {
            logger.error("Failed to convert DDL", e);
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }

    @McpTool(name = "cleanup_local_cache", description = "Clean up local cache for DMS SC project using S3 path")
    public Map<String, Object> cleanupLocalCache(String s3Path) {
        s3Path = getS3Path(s3Path);
        logger.info("Cleaning up cache for: {}", s3Path);
        Map<String, Object> result = new HashMap<>();
        
        try {
            Path targetPath = (s3Path == null || s3Path.isEmpty()) ? 
                Paths.get(System.getProperty("user.home"), ".oma-sc") : getLocalPathFromS3(s3Path);
            
            if (!Files.exists(targetPath)) {
                result.put("success", true);
                result.put("message", "Path does not exist");
                return result;
            }
            
            long deletedCount = Files.walk(targetPath).sorted(Comparator.reverseOrder())
                .peek(p -> { try { Files.delete(p); } catch (IOException e) {} }).count();
            
            result.put("success", true);
            result.put("deleted_items", deletedCount);
            result.put("path", targetPath.toString());
            
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
        return Paths.get(System.getProperty("user.home"), ".oma-sc", bucket, sanitizedPrefix);
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
        ListObjectsV2Request request = ListObjectsV2Request.builder().bucket(bucket).prefix(prefix).build();
        ListObjectsV2Response response;
        do {
            response = s3Client.listObjectsV2(request);
            objects.addAll(response.contents());
            request = request.toBuilder().continuationToken(response.nextContinuationToken()).build();
        } while (response.isTruncated());
        return objects;
    }

    private String getS3ObjectContent(S3Client s3Client, String bucket, String key) throws IOException {
        ResponseBytes<GetObjectResponse> objectBytes = s3Client.getObjectAsBytes(
            GetObjectRequest.builder().bucket(bucket).key(key).build()
        );
        return new String(objectBytes.asByteArray(), java.nio.charset.StandardCharsets.UTF_8);
    }

    private Map<String, Object> performAnalysis(Path basePath, String projectId) throws IOException {
        Map<String, Object> analysis = new HashMap<>();
        
        // Parallel execution using CompletableFuture
        try {
            var serversFuture = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try { return extractServerDetails(basePath); } 
                catch (IOException e) { throw new RuntimeException(e); }
            });
            
            var tablesFuture = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try { return extractTableMappings(basePath); } 
                catch (IOException e) { throw new RuntimeException(e); }
            });
            
            var viewsFuture = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try { return extractObjectMappings(basePath, "view", "Views"); } 
                catch (IOException e) { throw new RuntimeException(e); }
            });
            
            var functionsFuture = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try { return extractObjectMappings(basePath, "function", "Functions"); } 
                catch (IOException e) { throw new RuntimeException(e); }
            });
            
            var proceduresFuture = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try { return extractObjectMappings(basePath, "procedure", "Procedures"); } 
                catch (IOException e) { throw new RuntimeException(e); }
            });
            
            var ddlFuture = java.util.concurrent.CompletableFuture.runAsync(() -> {
                try { extractAndSaveDDLs(basePath); } 
                catch (IOException e) { throw new RuntimeException(e); }
            });
            
            // Wait for all tasks to complete
            java.util.concurrent.CompletableFuture.allOf(
                serversFuture, tablesFuture, viewsFuture, 
                functionsFuture, proceduresFuture, ddlFuture
            ).join();
            
            // Collect results
            analysis.put("servers", serversFuture.join());
            analysis.put("table_mappings", tablesFuture.join());
            analysis.put("view_mappings", viewsFuture.join());
            analysis.put("function_mappings", functionsFuture.join());
            analysis.put("procedure_mappings", proceduresFuture.join());
            
        } catch (Exception e) {
            throw new IOException("Parallel analysis failed", e);
        }
        
        Path analysisFile = basePath.resolve("analysis_results.json");
        objectMapper.writerWithDefaultPrettyPrinter().writeValue(analysisFile.toFile(), analysis);
        return analysis;
    }
    
    private List<Map<String, Object>> extractServerDetails(Path basePath) throws IOException {
        return Files.walk(basePath).filter(p -> p.toString().matches(".*[/\\\\][st]-server$"))
            .map(this::parseServerFile).filter(Objects::nonNull).collect(Collectors.toList());
    }

    private Map<String, Object> parseServerFile(Path file) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode server = json.at("/content/0/children/0");
            return Map.of("server_type", file.toString().contains("/t-server") ? "target" : "source",
                "server_name", server.path("name").asText(), "vendor", server.at("/server_info/vendorName").asText());
        } catch (Exception e) { return null; }
    }

    private List<Map<String, Object>> extractTableMappings(Path basePath) throws IOException {
        Map<String, Map<String, Object>> sourceTables = new HashMap<>();
        Map<String, Map<String, Object>> targetTables = new HashMap<>();
        Files.walk(basePath).filter(Files::isRegularFile)
            .filter(p -> p.getFileName().toString().matches("Schemas\\.[^.]+\\.Tables\\.[^.]+$") && p.toString().contains("/s-"))
            .forEach(p -> loadTableFile(p, sourceTables));
        Files.walk(basePath).filter(Files::isRegularFile)
            .filter(p -> p.getFileName().toString().matches("Schemas\\.[^.]+\\.Tables\\.[^.]+$") && p.toString().contains("/t-"))
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
                    String key = file.toString().contains("/s-") ? 
                        table.at("/synchronization_object/name").asText() : table.path("id").asText();
                    if (!key.isEmpty()) {
                        map.put(key, Map.of("schema", table.at("/locator/schema-name").asText(), "name", tableName, "file", file));
                    }
                }
            }
        } catch (Exception e) {}
    }
    
    private List<Map<String, Object>> matchTableMappings(Map<String, Map<String, Object>> source, Map<String, Map<String, Object>> target) {
        return source.entrySet().stream().filter(e -> target.containsKey(e.getKey())).map(e -> {
            Map<String, Object> src = e.getValue();
            Map<String, Object> trg = target.get(e.getKey());
            return Map.of("src_schema", src.get("schema"), "src_name", src.get("name"), 
                "trg_schema", trg.get("schema"), "trg_name", trg.get("name"));
        }).collect(Collectors.toList());
    }

    private List<Map<String, Object>> extractObjectMappings(Path basePath, String objectType, String category) throws IOException {
        Map<String, Map<String, Object>> sourceObjects = new HashMap<>();
        Map<String, Map<String, Object>> targetObjects = new HashMap<>();
        Files.walk(basePath).filter(Files::isRegularFile)
            .filter(p -> p.getFileName().toString().contains("." + category + ".") && p.toString().contains("/s-"))
            .forEach(p -> loadObjectFile(p, sourceObjects, objectType));
        Files.walk(basePath).filter(Files::isRegularFile)
            .filter(p -> p.getFileName().toString().contains("." + category + ".") && p.toString().contains("/t-"))
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
                String key = file.toString().contains("/s-") ? 
                    obj.at("/synchronization_object/name").asText() : obj.path("id").asText();
                if (!key.isEmpty()) {
                    map.put(key, Map.of("schema", obj.at("/locator/schema-name").asText(), "name", name, "file", file));
                }
            }
        } catch (Exception e) {}
    }
    
    private List<Map<String, Object>> matchObjectMappings(Map<String, Map<String, Object>> source, Map<String, Map<String, Object>> target) {
        return source.entrySet().stream().filter(e -> target.containsKey(e.getKey())).map(e -> {
            Map<String, Object> src = e.getValue();
            Map<String, Object> trg = target.get(e.getKey());
            return Map.of("src_schema", src.get("schema"), "src_name", src.get("name"), 
                "trg_schema", trg.get("schema"), "trg_name", trg.get("name"));
        }).collect(Collectors.toList());
    }

    private void extractAndSaveDDLs(Path basePath) throws IOException {
        Path sourceDdlDir = basePath.resolve("ddl/source");
        Path targetDdlDir = basePath.resolve("ddl/target");
        Files.createDirectories(sourceDdlDir);
        Files.createDirectories(targetDdlDir);
        Files.walk(basePath).filter(p -> p.toString().endsWith(".json") || p.toString().matches(".*[^.]+$"))
            .forEach(p -> extractDDL(p, sourceDdlDir, targetDdlDir));
    }

    private void extractDDL(Path file, Path sourceDdlDir, Path targetDdlDir) {
        try {
            JsonNode json = objectMapper.readTree(file.toFile());
            JsonNode content = json.at("/content/0");
            String ddl = content.path("sql").asText("");
            if (ddl.isEmpty() || "null".equalsIgnoreCase(ddl)) ddl = content.path("ddl").asText("");
            if (ddl.isEmpty() || "null".equalsIgnoreCase(ddl)) return;
            String schema = content.at("/locator/schema-name").asText("");
            String name = content.path("name").asText("");
            String type = content.path("type").asText("");
            if (schema.isEmpty() || name.isEmpty()) return;
            Path ddlDir = file.toString().contains("/s-") ? sourceDdlDir : targetDdlDir;
            String filename = String.format("%s_%s_%s.sql", schema, type, name).replaceAll("[^a-zA-Z0-9_.-]", "_");
            Files.writeString(ddlDir.resolve(filename), ddl);
        } catch (Exception e) {}
    }
    
    private Map<String, Object> filterByObjectType(Map<String, Object> analysis, String objectType) {
        Map<String, Object> filtered = new HashMap<>();
        filtered.put("success", analysis.get("success"));
        filtered.put("local_base", analysis.get("local_base"));
        String mappingKey = objectType + "_mappings";
        if (analysis.containsKey(mappingKey)) filtered.put(mappingKey, analysis.get(mappingKey));
        return filtered;
    }
    
    private Map<String, Object> filterBySchema(Map<String, Object> analysis, String schemaName) {
        Map<String, Object> filtered = new HashMap<>();
        filtered.put("success", analysis.get("success"));
        filtered.put("local_base", analysis.get("local_base"));
        for (Map.Entry<String, Object> entry : analysis.entrySet()) {
            if (entry.getKey().endsWith("_mappings") && entry.getValue() instanceof List) {
                List<Map<String, Object>> mappings = (List<Map<String, Object>>) entry.getValue();
                List<Map<String, Object>> filteredMappings = mappings.stream()
                    .filter(m -> schemaName.equals(((String) m.get("src_schema")).toLowerCase()))
                    .collect(Collectors.toList());
                if (!filteredMappings.isEmpty()) filtered.put(entry.getKey(), filteredMappings);
            }
        }
        return filtered;
    }
    
    private Map<String, Object> filterByObjectName(Map<String, Object> analysis, String objectName) {
        Map<String, Object> filtered = new HashMap<>();
        filtered.put("success", analysis.get("success"));
        filtered.put("local_base", analysis.get("local_base"));
        for (Map.Entry<String, Object> entry : analysis.entrySet()) {
            if (entry.getKey().endsWith("_mappings") && entry.getValue() instanceof List) {
                List<Map<String, Object>> mappings = (List<Map<String, Object>>) entry.getValue();
                List<Map<String, Object>> filteredMappings = mappings.stream()
                    .filter(m -> objectName.equals(((String) m.get("src_name")).toLowerCase()))
                    .collect(Collectors.toList());
                if (!filteredMappings.isEmpty()) filtered.put(entry.getKey(), filteredMappings);
            }
        }
        return filtered;
    }
    
    private boolean matchesPattern(String filename, String pattern) {
        return filename.matches(pattern.replace("*", ".*"));
    }
}
