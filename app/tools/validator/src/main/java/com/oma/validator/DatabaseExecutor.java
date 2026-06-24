package com.oma.validator;

import java.util.Map;

/**
 * Database executor interface
 */
public interface DatabaseExecutor {

    /**
     * Execute SQL and return JSON result
     *
     * @param sqlId SQL statement ID (namespace.id)
     * @param params Parameters
     * @return JSON string of results
     */
    String execute(String sqlId, Map<String, Object> params) throws Exception;

    /**
     * Set Extension for bind variable substitution
     *
     * @param extension Extension instance
     * @param dbType Database type ("oracle" or "postgres")
     */
    void setExtension(Extension extension, String dbType);

    /**
     * Close resources
     */
    void close();
}
