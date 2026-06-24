package com.oma.validator;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Extension system for custom bind variable substitution
 * Provides database-specific values for framework variables (e.g., GRIDPAGING, sysdate)
 */
public class Extension {
    private boolean enabled;
    private Map<String, Map<String, Object>> variables;
    private static final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Load extension configuration from JSON file
     */
    public static Extension load(String configPath) throws IOException {
        File configFile = new File(configPath);
        if (!configFile.exists()) {
            System.out.println("⚠ Extension config not found: " + configPath);
            return createDisabled();
        }

        JsonNode root = objectMapper.readTree(configFile);
        Extension extension = new Extension();

        extension.enabled = root.path("enabled").asBoolean(false);
        extension.variables = new HashMap<>();

        if (!extension.enabled) {
            System.out.println("⚠ Extension is disabled");
            return extension;
        }

        // Parse variables
        JsonNode varsNode = root.path("variables");
        if (varsNode.isObject()) {
            varsNode.fields().forEachRemaining(entry -> {
                String varName = entry.getKey();
                JsonNode dbValues = entry.getValue();

                Map<String, Object> dbMap = new HashMap<>();
                if (dbValues.isObject()) {
                    dbValues.fields().forEachRemaining(dbEntry -> {
                        JsonNode valueNode = dbEntry.getValue();
                        Object value;

                        if (valueNode.isArray()) {
                            // Parse as List
                            List<String> list = new ArrayList<>();
                            valueNode.forEach(item -> list.add(item.asText()));
                            value = list;
                        } else {
                            // Parse as String
                            value = valueNode.asText();
                        }

                        dbMap.put(dbEntry.getKey(), value);
                    });
                }
                extension.variables.put(varName, dbMap);
            });
        }

        System.out.println("✓ Extension loaded with " + extension.variables.size() + " variables");
        return extension;
    }

    /**
     * Create disabled extension instance
     */
    public static Extension createDisabled() {
        Extension extension = new Extension();
        extension.enabled = false;
        extension.variables = new HashMap<>();
        return extension;
    }

    /**
     * Check if extension is enabled
     */
    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Get bind variable value for specific database type
     * @param varName Variable name (e.g., "GRIDPAGING_ROWNUMTYPE_TOP", "sysdate")
     * @param dbType Database type ("oracle" or "postgres")
     * @return Value for the variable (String or List<String>), or null if not found
     */
    public Object getValue(String varName, String dbType) {
        if (!enabled) {
            return null;
        }

        Map<String, Object> dbMap = variables.get(varName);
        if (dbMap == null) {
            return null;
        }

        return dbMap.get(dbType.toLowerCase());
    }

    /**
     * Check if variable is managed by Extension
     */
    public boolean hasVariable(String varName) {
        return enabled && variables.containsKey(varName);
    }

    /**
     * Get all managed variable names
     */
    public Iterable<String> getVariableNames() {
        return variables.keySet();
    }
}
