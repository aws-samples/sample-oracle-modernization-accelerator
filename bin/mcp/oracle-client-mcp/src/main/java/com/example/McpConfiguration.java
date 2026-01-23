package com.example;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class McpConfiguration {

    @Bean
    public OracleMcpTools oracleMcpTools() {
        return new OracleMcpTools();
    }
}
