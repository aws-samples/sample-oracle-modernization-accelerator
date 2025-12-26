package com.example;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;
import software.amazon.awssdk.services.secretsmanager.SecretsManagerClient;
import software.amazon.awssdk.services.secretsmanager.model.GetSecretValueRequest;
import software.amazon.awssdk.regions.Region;

import javax.sql.DataSource;


@Configuration
public class DatabaseConfig {

    private static final Logger logger = LoggerFactory.getLogger(DatabaseConfig.class);

    @Value("${mcp.db.connection.type:password}")
    private String connectionType;

    @Value("${mcp.db.connection.detail}")
    private String connectionDetail;

    @Value("${mcp.db.connection.readonly:false}")
    private boolean readOnly;


    @Bean
    @Primary
    public DataSource dataSource() {
        logger.info("Creating main dataSource with readonly={}", readOnly);
        return createDataSource(readOnly);
    }

    @Bean
    @Primary
    public JdbcTemplate jdbcTemplate() {
        return new JdbcTemplate(dataSource());
    }

    private DataSource createDataSource(boolean isReadOnly) {
        logger.info("createDataSource called with isReadOnly={}", isReadOnly);
        HikariConfig config = new HikariConfig();
        
        if ("secretsmanager".equals(connectionType)) {
            configureFromSecretsManager(config);
        } else {
            configureFromPassword(config);
        }
        
        config.setConnectionTimeout(20000);
        config.setMaximumPoolSize(5);
        config.setMinimumIdle(1);
        config.setIdleTimeout(300000);
        config.setMaxLifetime(1200000);
        
        // Ensure read-only is enforced at connection level
        if (isReadOnly) {
            logger.info("Setting connection init SQL for READ ONLY");
            config.setConnectionInitSql("SET default_transaction_read_only = true;");
        } else {
            logger.info("Setting connection init SQL for READ WRITE");
            config.setConnectionInitSql("SET default_transaction_read_only = false;");
        }
        
        return new HikariDataSource(config);
    }

    private void configureFromPassword(HikariConfig config) {
        // Parse username:password@hostname:port/db
        String[] parts = connectionDetail.split("@");
        String[] userPass = parts[0].split(":");
        String[] hostPortDb = parts[1].split("/");
        String[] hostPort = hostPortDb[0].split(":");
        
        config.setJdbcUrl("jdbc:postgresql://" + hostPort[0] + ":" + hostPort[1] + "/" + hostPortDb[1]);
        config.setUsername(userPass[0]);
        config.setPassword(userPass[1]);
        config.setDriverClassName("org.postgresql.Driver");
    }

    private void configureFromSecretsManager(HikariConfig config) {
        try {
            // Extract region from ARN: arn:aws:secretsmanager:us-west-2:account:secret:name
            String region = connectionDetail.split(":")[3];
            logger.info("Using region: {}", region);
            logger.info("Secret ARN: {}", connectionDetail);

            try (SecretsManagerClient client = SecretsManagerClient.builder()
                    .region(Region.of(region))
                    .build()) {
                String secretValue = client.getSecretValue(
                    GetSecretValueRequest.builder().secretId(connectionDetail).build()
                ).secretString();

                // logger.info("Retrieved secret value: {}", secretValue);

                ObjectMapper mapper = new ObjectMapper();
                JsonNode secret = mapper.readTree(secretValue);

                String host = secret.get("host").asText();
                int port = secret.get("port").asInt();
                String dbname = secret.has("dbname") ? secret.get("dbname").asText() : "postgres";
                String username = secret.get("username").asText();
                String password = secret.get("password").asText();

                // logger.info("host={}, port={}, dbname={}, username={}", host, port, dbname, username);

                config.setJdbcUrl("jdbc:postgresql://" + host + ":" + port + "/" + dbname);
                config.setUsername(username);
                config.setPassword(password);
                config.setDriverClassName("org.postgresql.Driver");
                
                logger.info("Database configuration completed - JDBC URL: jdbc:postgresql://{}:{}/{}", host, port, dbname);
            }
        } catch (Exception e) {
            logger.error("Failed to retrieve database credentials: {}", e.getMessage());
            throw new RuntimeException("Failed to retrieve database credentials from Secrets Manager", e);
        }
    }
}
