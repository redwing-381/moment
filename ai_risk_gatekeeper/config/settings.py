"""
Configuration management for the AI Risk Gatekeeper system.

Handles loading configuration from environment variables and YAML files
for Confluent Cloud and Vertex AI credentials.
"""

import os
import yaml
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


@dataclass
class KafkaConfig:
    """Configuration for Confluent Cloud Kafka connection."""
    bootstrap_servers: str
    security_protocol: str
    sasl_mechanism: str
    sasl_username: str
    sasl_password: str
    
    # Topic names
    enterprise_action_events_topic: str = "enterprise-action-events"
    risk_signals_topic: str = "risk-signals"
    risk_decisions_topic: str = "risk-decisions"
    
    # Consumer/Producer settings
    consumer_group_id: str = "ai-risk-gatekeeper"
    auto_offset_reset: str = "latest"


@dataclass
class SchemaRegistryConfig:
    """Configuration for Confluent Schema Registry."""
    url: str
    api_key: str
    api_secret: str


@dataclass
class KsqlDBConfig:
    """Configuration for Confluent ksqlDB."""
    endpoint: str
    api_key: str
    api_secret: str


@dataclass
class ConfluentCloudConfig:
    """Configuration for Confluent Cloud Metrics API."""
    api_key: str
    api_secret: str
    cluster_id: str
    environment_id: str


@dataclass
class VertexAIConfig:
    """Configuration for Google Cloud Vertex AI integration."""
    project_id: str
    location: str
    model_name: str = "gemini-1.5-flash"
    credentials_path: Optional[str] = None
    
    # AI decision parameters
    max_tokens: int = 1000
    temperature: float = 0.1
    timeout_seconds: int = 10


@dataclass
class SystemConfig:
    """Overall system configuration."""
    kafka: KafkaConfig
    vertex_ai: VertexAIConfig
    schema_registry: Optional[SchemaRegistryConfig] = None
    ksqldb: Optional[KsqlDBConfig] = None
    confluent_cloud: Optional[ConfluentCloudConfig] = None
    
    # Performance settings
    max_processing_time_ms: int = 350
    event_producer_interval_ms: int = 100
    signal_processing_timeout_ms: int = 50
    decision_timeout_ms: int = 200
    action_timeout_ms: int = 100
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"


class ConfigManager:
    """Manages loading and validation of system configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to YAML configuration file
        """
        self.config_file = config_file or "config.yaml"
        self._config: Optional[SystemConfig] = None
    
    def load_config(self) -> SystemConfig:
        """
        Load configuration from environment variables and config file.
        
        Returns:
            SystemConfig: Loaded and validated configuration
            
        Raises:
            ValueError: If required configuration is missing
        """
        if self._config is not None:
            return self._config
        
        # Load from YAML file if it exists
        yaml_config = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                yaml_config = yaml.safe_load(f) or {}
        
        # Build Kafka configuration
        kafka_config = KafkaConfig(
            bootstrap_servers=self._get_config_value(
                "KAFKA_BOOTSTRAP_SERVERS", 
                yaml_config.get("kafka", {}).get("bootstrap_servers")
            ),
            security_protocol=self._get_config_value(
                "KAFKA_SECURITY_PROTOCOL", 
                yaml_config.get("kafka", {}).get("security_protocol", "SASL_SSL")
            ),
            sasl_mechanism=self._get_config_value(
                "KAFKA_SASL_MECHANISM", 
                yaml_config.get("kafka", {}).get("sasl_mechanism", "PLAIN")
            ),
            sasl_username=self._get_config_value(
                "KAFKA_SASL_USERNAME", 
                yaml_config.get("kafka", {}).get("sasl_username")
            ),
            sasl_password=self._get_config_value(
                "KAFKA_SASL_PASSWORD", 
                yaml_config.get("kafka", {}).get("sasl_password")
            ),
            enterprise_action_events_topic=self._get_config_value(
                "KAFKA_ENTERPRISE_EVENTS_TOPIC",
                yaml_config.get("kafka", {}).get("enterprise_action_events_topic", "enterprise-action-events")
            ),
            risk_signals_topic=self._get_config_value(
                "KAFKA_RISK_SIGNALS_TOPIC",
                yaml_config.get("kafka", {}).get("risk_signals_topic", "risk-signals")
            ),
            risk_decisions_topic=self._get_config_value(
                "KAFKA_RISK_DECISIONS_TOPIC",
                yaml_config.get("kafka", {}).get("risk_decisions_topic", "risk-decisions")
            ),
            consumer_group_id=self._get_config_value(
                "KAFKA_CONSUMER_GROUP_ID",
                yaml_config.get("kafka", {}).get("consumer_group_id", "ai-risk-gatekeeper")
            )
        )
        
        # Build Vertex AI configuration
        vertex_ai_config = VertexAIConfig(
            project_id=self._get_config_value(
                "VERTEX_AI_PROJECT_ID", 
                yaml_config.get("vertex_ai", {}).get("project_id")
            ),
            location=self._get_config_value(
                "VERTEX_AI_LOCATION", 
                yaml_config.get("vertex_ai", {}).get("location", "us-central1")
            ),
            model_name=self._get_config_value(
                "VERTEX_AI_MODEL_NAME", 
                yaml_config.get("vertex_ai", {}).get("model_name", "gemini-1.5-flash")
            ),
            credentials_path=self._get_config_value(
                "GOOGLE_APPLICATION_CREDENTIALS", 
                yaml_config.get("vertex_ai", {}).get("credentials_path"),
                required=False
            )
        )
        
        # Build Schema Registry configuration (optional)
        schema_registry_config = None
        sr_url = self._get_config_value("SCHEMA_REGISTRY_URL", None, required=False)
        sr_key = self._get_config_value("SCHEMA_REGISTRY_API_KEY", None, required=False)
        sr_secret = self._get_config_value("SCHEMA_REGISTRY_API_SECRET", None, required=False)
        if sr_url and sr_key and sr_secret:
            schema_registry_config = SchemaRegistryConfig(
                url=sr_url,
                api_key=sr_key,
                api_secret=sr_secret
            )
        
        # Build ksqlDB configuration (optional)
        ksqldb_config = None
        ksql_endpoint = self._get_config_value("KSQLDB_ENDPOINT", None, required=False)
        ksql_key = self._get_config_value("KSQLDB_API_KEY", None, required=False)
        ksql_secret = self._get_config_value("KSQLDB_API_SECRET", None, required=False)
        if ksql_endpoint and ksql_key and ksql_secret:
            ksqldb_config = KsqlDBConfig(
                endpoint=ksql_endpoint,
                api_key=ksql_key,
                api_secret=ksql_secret
            )
        
        # Build Confluent Cloud configuration (optional)
        confluent_cloud_config = None
        cc_key = self._get_config_value("CONFLUENT_CLOUD_API_KEY", None, required=False)
        cc_secret = self._get_config_value("CONFLUENT_CLOUD_API_SECRET", None, required=False)
        cc_cluster = self._get_config_value("CONFLUENT_CLUSTER_ID", None, required=False)
        cc_env = self._get_config_value("CONFLUENT_ENVIRONMENT_ID", None, required=False)
        if cc_key and cc_secret and cc_cluster and cc_env:
            confluent_cloud_config = ConfluentCloudConfig(
                api_key=cc_key,
                api_secret=cc_secret,
                cluster_id=cc_cluster,
                environment_id=cc_env
            )
        
        # Build system configuration
        self._config = SystemConfig(
            kafka=kafka_config,
            vertex_ai=vertex_ai_config,
            schema_registry=schema_registry_config,
            ksqldb=ksqldb_config,
            confluent_cloud=confluent_cloud_config,
            log_level=self._get_config_value(
                "LOG_LEVEL", 
                yaml_config.get("system", {}).get("log_level", "INFO"),
                required=False
            )
        )
        
        return self._config
    
    def _get_config_value(self, env_var: str, yaml_value: Any, required: bool = True) -> str:
        """
        Get configuration value from environment variable or YAML, with precedence.
        
        Args:
            env_var: Environment variable name
            yaml_value: Value from YAML configuration
            required: Whether the value is required
            
        Returns:
            Configuration value
            
        Raises:
            ValueError: If required value is missing
        """
        value = os.getenv(env_var) or yaml_value
        
        if required and not value:
            raise ValueError(f"Required configuration missing: {env_var}")
        
        return value
    
    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present and valid.
        
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        config = self.load_config()
        
        # Validate Kafka configuration
        if not config.kafka.bootstrap_servers:
            raise ValueError("Kafka bootstrap servers not configured")
        
        if not config.kafka.sasl_username or not config.kafka.sasl_password:
            raise ValueError("Kafka SASL credentials not configured")
        
        # Validate Vertex AI configuration
        if not config.vertex_ai.project_id:
            raise ValueError("Vertex AI project ID not configured")
        
        return True


# Global configuration manager instance
config_manager = ConfigManager()