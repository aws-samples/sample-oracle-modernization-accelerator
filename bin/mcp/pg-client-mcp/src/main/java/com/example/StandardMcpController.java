package com.example;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

@RestController
public class StandardMcpController {
    
    private static final Logger log = LoggerFactory.getLogger(StandardMcpController.class);
    
    @Autowired
    private PostgreSQLMcpTools tools;
    
    private ObjectMapper mapper = new ObjectMapper();
    
    @PostMapping("/mcp")
    public ResponseEntity<String> handleMcpRequest(@RequestBody String jsonRpc) {
        log.info("Gateway MCP request: {}", jsonRpc);
        
        try {
            Map<String, Object> request = mapper.readValue(jsonRpc, Map.class);
            String method = (String) request.get("method");
            Object id = request.get("id");
            
            Map<String, Object> response = new HashMap<>();
            response.put("jsonrpc", "2.0");
            response.put("id", id);
            
            switch (method) {
                case "initialize":
                    // Gateway requires 2025-06-18
                    Map<String, Object> result = new HashMap<>();
                    result.put("protocolVersion", "2025-06-18");
                    result.put("serverInfo", Map.of("name", "pg-client-mcp", "version", "1.0.0"));
                    result.put("capabilities", Map.of("tools", Map.of()));
                    response.put("result", result);
                    break;
                
                case "notifications/initialized":
                    response.put("result", Map.of());
                    break;
                    
                case "tools/list":
                    List<Map<String, Object>> toolsList = new ArrayList<>();
                    toolsList.add(Map.of(
                        "name", "executeSql",
                        "description", "Execute SQL query on PostgreSQL database",
                        "inputSchema", Map.of(
                            "type", "object",
                            "properties", Map.of(
                                "sql", Map.of("type", "string", "description", "SQL query to execute"),
                                "maxRows", Map.of("type", "integer", "description", "Maximum rows to return")
                            ),
                            "required", List.of("sql")
                        )
                    ));
                    toolsList.add(Map.of(
                        "name", "executeTestCaseReadOnly",
                        "description", "Execute test case in read-only mode",
                        "inputSchema", Map.of(
                            "type", "object",
                            "properties", Map.of(
                                "sql", Map.of("type", "string", "description", "SQL query to test")
                            ),
                            "required", List.of("sql")
                        )
                    ));
                    toolsList.add(Map.of(
                        "name", "executeTestCaseRollback",
                        "description", "Execute test case with automatic rollback",
                        "inputSchema", Map.of(
                            "type", "object",
                            "properties", Map.of(
                                "sql", Map.of("type", "string", "description", "SQL query to test")
                            ),
                            "required", List.of("sql")
                        )
                    ));
                    response.put("result", Map.of("tools", toolsList));
                    break;
                    
                default:
                    response.put("error", Map.of("code", -32601, "message", "Method not found"));
            }
            
            String responseJson = mapper.writeValueAsString(response);
            log.info("Gateway MCP response: {}", responseJson);
            
            return ResponseEntity.ok()
                .header("Content-Type", "application/json")
                .body(responseJson);
                
        } catch (Exception e) {
            log.error("MCP error: {}", e.getMessage(), e);
            return ResponseEntity.status(500)
                .body("{\"jsonrpc\":\"2.0\",\"error\":{\"code\":-32603,\"message\":\"Internal error\"}}");
        }
    }
}
