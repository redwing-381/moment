"""
Unit tests for configuration management.

Tests configuration loading from environment variables and YAML files.
"""

import os
import tempfile
import pytest
from unittest.mock import patch

from ai_risk_gatekeeper.config.settings import ConfigManager


# Environment variables to clear for isolated tests
ENV_VARS_TO_CLEAR = [
    'KAFKA_BOOTSTRAP_SERVERS', 'KAFKA_SECURITY_PROTOCOL', 'KAFKA_SASL_MECHANISM',
    'KAFKA_SASL_USERNAME', 'KAFKA_SASL_PASSWORD', 'VERTEX_AI_PROJECT_ID',
    'VERTEX_AI_LOCATION', 'VERTEX_AI_MODEL_NAME', 'GOOGLE_APPLICATION_CREDENTIALS'
]


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_load_config_from_env_vars(self):
        """Test loading configuration from environment variables."""
        env_override = {k: '' for k in ENV_VARS_TO_CLEAR}
        env_override.update({
            'KAFKA_BOOTSTRAP_SERVERS': 'test-cluster.confluent.cloud:9092',
            'KAFKA_SASL_USERNAME': 'test-key',
            'KAFKA_SASL_PASSWORD': 'test-secret',
            'VERTEX_AI_PROJECT_ID': 'test-project',
            'VERTEX_AI_LOCATION': 'us-central1'
        })
        
        with patch.dict(os.environ, env_override, clear=False):
            config_manager = ConfigManager(config_file='nonexistent.yaml')
            config = config_manager.load_config()
            
            assert config.kafka.bootstrap_servers == 'test-cluster.confluent.cloud:9092'
            assert config.kafka.sasl_username == 'test-key'
            assert config.kafka.sasl_password == 'test-secret'
            assert config.vertex_ai.project_id == 'test-project'
            assert config.vertex_ai.location == 'us-central1'
    
    def test_load_config_from_yaml(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
kafka:
  bootstrap_servers: "yaml-cluster.confluent.cloud:9092"
  sasl_username: "yaml-key"
  sasl_password: "yaml-secret"

vertex_ai:
  project_id: "yaml-project"
  location: "us-west1"
"""
        # Clear all env vars so YAML values are used
        env_override = {k: '' for k in ENV_VARS_TO_CLEAR}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                with patch.dict(os.environ, env_override, clear=False):
                    config_manager = ConfigManager(config_file=f.name)
                    config = config_manager.load_config()
                    
                    assert config.kafka.bootstrap_servers == 'yaml-cluster.confluent.cloud:9092'
                    assert config.kafka.sasl_username == 'yaml-key'
                    assert config.kafka.sasl_password == 'yaml-secret'
                    assert config.vertex_ai.project_id == 'yaml-project'
                    assert config.vertex_ai.location == 'us-west1'
            finally:
                os.unlink(f.name)
    
    def test_env_vars_override_yaml(self):
        """Test that environment variables override YAML configuration."""
        yaml_content = """
kafka:
  bootstrap_servers: "yaml-cluster.confluent.cloud:9092"
  sasl_username: "yaml-key"
  sasl_password: "yaml-secret"

vertex_ai:
  project_id: "yaml-project"
"""
        # Clear env vars except the ones we want to override
        env_override = {k: '' for k in ENV_VARS_TO_CLEAR}
        env_override.update({
            'KAFKA_BOOTSTRAP_SERVERS': 'env-cluster.confluent.cloud:9092',
            'VERTEX_AI_PROJECT_ID': 'env-project'
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                with patch.dict(os.environ, env_override, clear=False):
                    config_manager = ConfigManager(config_file=f.name)
                    config = config_manager.load_config()
                    
                    # Environment variables should override YAML
                    assert config.kafka.bootstrap_servers == 'env-cluster.confluent.cloud:9092'
                    assert config.vertex_ai.project_id == 'env-project'
                    
                    # YAML values should be used where env vars are not set
                    assert config.kafka.sasl_username == 'yaml-key'
                    assert config.kafka.sasl_password == 'yaml-secret'
            finally:
                os.unlink(f.name)
    
    def test_missing_required_config_raises_error(self):
        """Test that missing required configuration raises ValueError."""
        env_override = {k: '' for k in ENV_VARS_TO_CLEAR}
        
        with patch.dict(os.environ, env_override, clear=False):
            config_manager = ConfigManager(config_file='nonexistent.yaml')
            
            with pytest.raises(ValueError, match="Required configuration missing"):
                config_manager.load_config()
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        env_override = {k: '' for k in ENV_VARS_TO_CLEAR}
        env_override.update({
            'KAFKA_BOOTSTRAP_SERVERS': 'test-cluster.confluent.cloud:9092',
            'KAFKA_SASL_USERNAME': 'test-key',
            'KAFKA_SASL_PASSWORD': 'test-secret',
            'VERTEX_AI_PROJECT_ID': 'test-project'
        })
        
        with patch.dict(os.environ, env_override, clear=False):
            config_manager = ConfigManager(config_file='nonexistent.yaml')
            assert config_manager.validate_config() is True
    
    def test_validate_config_missing_kafka_credentials(self):
        """Test validation fails with missing Kafka credentials."""
        env_override = {k: '' for k in ENV_VARS_TO_CLEAR}
        env_override.update({
            'KAFKA_BOOTSTRAP_SERVERS': 'test-cluster.confluent.cloud:9092',
            'VERTEX_AI_PROJECT_ID': 'test-project'
            # Missing KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD
        })
        
        with patch.dict(os.environ, env_override, clear=False):
            config_manager = ConfigManager(config_file='nonexistent.yaml')
            
            with pytest.raises(ValueError, match="Required configuration missing: KAFKA_SASL_USERNAME"):
                config_manager.validate_config()