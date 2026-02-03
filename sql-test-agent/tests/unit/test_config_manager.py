"""Unit tests for ConfigManager."""

import os
import pytest

from agent.config_manager import ConfigManager, DatabaseCredentials
from models.enums import DatabaseType
from utils.error_handler import ConfigurationError


class TestDatabaseCredentials:
    """Test DatabaseCredentials class."""
    
    def test_oracle_credentials_valid(self):
        """Test Oracle credentials validation."""
        creds = DatabaseCredentials(DatabaseType.ORACLE)
        creds.username = "user"
        creds.password = "pass"
        creds.connect_string = "host:1521:sid"
        
        assert creds.is_valid()
    
    def test_oracle_credentials_invalid(self):
        """Test Oracle credentials validation fails."""
        creds = DatabaseCredentials(DatabaseType.ORACLE)
        creds.username = "user"
        # Missing password and connect_string
        
        assert not creds.is_valid()
    
    def test_postgresql_credentials_valid(self):
        """Test PostgreSQL credentials validation."""
        creds = DatabaseCredentials(DatabaseType.POSTGRESQL)
        creds.username = "user"
        creds.password = "pass"
        creds.host = "localhost"
        creds.port = 5432
        creds.database = "testdb"
        
        assert creds.is_valid()
    
    def test_mysql_credentials_valid(self):
        """Test MySQL credentials validation."""
        creds = DatabaseCredentials(DatabaseType.MYSQL)
        creds.username = "user"
        creds.password = "pass"
        creds.host = "localhost"
        creds.port = 3306
        creds.database = "testdb"
        
        assert creds.is_valid()
    
    def test_credentials_repr_masks_password(self):
        """Test that password is masked in string representation."""
        creds = DatabaseCredentials(DatabaseType.ORACLE)
        creds.username = "user"
        creds.password = "secret"
        
        repr_str = repr(creds)
        assert "secret" not in repr_str
        assert "***" in repr_str


class TestConfigManager:
    """Test ConfigManager class."""
    
    @pytest.fixture
    def setup_env_vars(self):
        """Set up environment variables for testing."""
        # Save original env vars
        original_env = {}
        test_vars = {
            "ORACLE_SVC_USER": "testuser",
            "ORACLE_SVC_PASSWORD": "testpass",
            "ORACLE_SVC_CONNECT_STRING": "localhost:1521:testdb",
            "ORACLE_HOST": "localhost",
            "ORACLE_PORT": "1521",
            "ORACLE_SID": "testdb",
            "ANTHROPIC_API_KEY": "test_api_key",
            "MAX_RETRIES": "5",
            "MIN_CONFIDENCE_THRESHOLD": "0.8",
            "OMA_BASE_DIR": "/test/oma",
            "APPLICATION_NAME": "testapp",
            "SOURCE_DBMS_TYPE": "orcl",
            "TARGET_DBMS_TYPE": "postgres",
        }
        
        for key, value in test_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore original env vars
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    def test_load_from_environment(self, setup_env_vars):
        """Test loading configuration from environment variables."""
        manager = ConfigManager()
        config = manager.load_config()
        
        assert config.oracle_credentials.username == "testuser"
        assert config.oracle_credentials.password == "testpass"
        assert config.oracle_credentials.connect_string == "localhost:1521:testdb"
        assert config.llm_config.api_key == "test_api_key"
        assert config.retry_config.max_retries == 5
        assert config.retry_config.min_confidence_threshold == 0.8
        assert str(config.path_config.oma_base_dir) == "/test/oma"
        assert config.path_config.application_name == "testapp"
    
    def test_validation_fails_without_database(self):
        """Test validation fails when no database is configured."""
        # Set only LLM key
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        
        # Clear database env vars
        for key in ["ORACLE_SVC_USER", "ORACLE_SVC_PASSWORD", "ORACLE_SVC_CONNECT_STRING",
                    "PGUSER", "PGPASSWORD", "MYSQL_USER", "MYSQL_PASSWORD"]:
            os.environ.pop(key, None)
        
        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="At least one database"):
            manager.load_config()
    
    def test_validation_fails_without_llm_key(self, setup_env_vars):
        """Test validation fails when LLM API key is missing."""
        # Remove LLM keys
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        
        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="LLM API key"):
            manager.load_config()
    
    def test_get_db_credentials(self, setup_env_vars):
        """Test getting database credentials."""
        manager = ConfigManager()
        config = manager.load_config()
        
        oracle_creds = manager.get_db_credentials(DatabaseType.ORACLE)
        assert oracle_creds.username == "testuser"
        assert oracle_creds.is_valid()
    
    def test_get_db_credentials_not_configured(self, setup_env_vars):
        """Test getting credentials for unconfigured database."""
        manager = ConfigManager()
        config = manager.load_config()
        
        with pytest.raises(ConfigurationError, match="not configured"):
            manager.get_db_credentials(DatabaseType.MYSQL)
    
    def test_default_values(self, setup_env_vars):
        """Test default configuration values."""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Check defaults
        assert config.retry_config.retry_delay_seconds == 2
        assert config.comparison_config.acceptable_pass_rate == 0.95
        assert config.execution_config.batch_size == 10
        assert config.logging_config.log_level == "INFO"
        assert config.path_config.language == "en"
    
    def test_postgresql_credentials_from_oma_properties(self):
        """Test PostgreSQL credentials from OMA properties format."""
        os.environ["PGUSER"] = "pguser"
        os.environ["PGPASSWORD"] = "pgpass"
        os.environ["PGHOST"] = "pghost"
        os.environ["PGPORT"] = "5432"
        os.environ["PGDATABASE"] = "pgdb"
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        
        manager = ConfigManager()
        config = manager.load_config()
        
        assert config.postgresql_credentials.username == "pguser"
        assert config.postgresql_credentials.password == "pgpass"
        assert config.postgresql_credentials.host == "pghost"
        assert config.postgresql_credentials.port == 5432
        assert config.postgresql_credentials.database == "pgdb"
        
        # Cleanup
        for key in ["PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "PGDATABASE", "ANTHROPIC_API_KEY"]:
            os.environ.pop(key, None)
