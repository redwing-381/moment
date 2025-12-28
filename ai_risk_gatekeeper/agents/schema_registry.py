"""
Schema Registry client for Confluent Cloud.

Provides Avro schema management and serialization for enterprise action events.
"""

import io
import struct
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass


# Avro schema for EnterpriseActionEvent
ENTERPRISE_ACTION_EVENT_SCHEMA = {
    "type": "record",
    "name": "EnterpriseActionEvent",
    "namespace": "com.moment.risk",
    "fields": [
        {"name": "event_id", "type": "string"},
        {"name": "actor_id", "type": "string"},
        {"name": "action", "type": "string"},
        {"name": "role", "type": "string"},
        {"name": "frequency_last_60s", "type": "int"},
        {"name": "geo_change", "type": "boolean"},
        {"name": "timestamp", "type": "string"},
        {"name": "session_id", "type": "string"},
        {"name": "resource_sensitivity", "type": "string"},
        {"name": "risk_score", "type": ["null", "float"], "default": None}
    ]
}


@dataclass
class SchemaInfo:
    """Information about a registered schema."""
    schema_id: int
    version: int
    schema: Dict[str, Any]
    subject: str


class SchemaRegistryClient:
    """Client for Confluent Schema Registry."""
    
    def __init__(self, url: str, api_key: str, api_secret: str):
        """
        Initialize Schema Registry client.
        
        Args:
            url: Schema Registry URL
            api_key: API key for authentication
            api_secret: API secret for authentication
        """
        self.url = url.rstrip('/')
        self.auth = (api_key, api_secret)
        self._schema_cache: Dict[int, Dict[str, Any]] = {}
        self._id_cache: Dict[str, int] = {}
    
    def register_schema(self, subject: str, schema: Dict[str, Any]) -> int:
        """
        Register a schema with the registry.
        
        Args:
            subject: Subject name (typically topic-value or topic-key)
            schema: Avro schema as dictionary
            
        Returns:
            Schema ID
        """
        import json
        
        url = f"{self.url}/subjects/{subject}/versions"
        payload = {"schema": json.dumps(schema)}
        
        response = requests.post(
            url,
            json=payload,
            auth=self.auth,
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
        )
        response.raise_for_status()
        
        schema_id = response.json()["id"]
        self._schema_cache[schema_id] = schema
        self._id_cache[subject] = schema_id
        
        return schema_id
    
    def get_schema(self, schema_id: int) -> Dict[str, Any]:
        """
        Get schema by ID.
        
        Args:
            schema_id: Schema ID
            
        Returns:
            Schema as dictionary
        """
        import json
        
        if schema_id in self._schema_cache:
            return self._schema_cache[schema_id]
        
        url = f"{self.url}/schemas/ids/{schema_id}"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        
        schema = json.loads(response.json()["schema"])
        self._schema_cache[schema_id] = schema
        
        return schema
    
    def get_latest_version(self, subject: str) -> SchemaInfo:
        """
        Get the latest version of a schema for a subject.
        
        Args:
            subject: Subject name
            
        Returns:
            SchemaInfo with schema details
        """
        import json
        
        url = f"{self.url}/subjects/{subject}/versions/latest"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        
        data = response.json()
        schema = json.loads(data["schema"])
        
        return SchemaInfo(
            schema_id=data["id"],
            version=data["version"],
            schema=schema,
            subject=subject
        )
    
    def check_connection(self) -> bool:
        """Check if Schema Registry is reachable."""
        try:
            response = requests.get(f"{self.url}/subjects", auth=self.auth, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class AvroSerializer:
    """Avro serializer with Confluent wire format support."""
    
    MAGIC_BYTE = 0
    
    def __init__(self, registry_client: SchemaRegistryClient, schema: Dict[str, Any], subject: str):
        """
        Initialize Avro serializer.
        
        Args:
            registry_client: Schema Registry client
            schema: Avro schema
            subject: Subject name for schema registration
        """
        self.registry = registry_client
        self.schema = schema
        self.subject = subject
        self._schema_id: Optional[int] = None
        self._parsed_schema = None
    
    def _ensure_schema_registered(self) -> int:
        """Ensure schema is registered and return schema ID."""
        if self._schema_id is None:
            self._schema_id = self.registry.register_schema(self.subject, self.schema)
        return self._schema_id
    
    def _get_parsed_schema(self):
        """Get parsed fastavro schema."""
        if self._parsed_schema is None:
            import fastavro
            self._parsed_schema = fastavro.parse_schema(self.schema)
        return self._parsed_schema
    
    def serialize(self, data: Dict[str, Any]) -> bytes:
        """
        Serialize data to Avro with Confluent wire format.
        
        Wire format: [magic byte (1)] [schema id (4)] [avro data (n)]
        
        Args:
            data: Dictionary to serialize
            
        Returns:
            Serialized bytes
        """
        import fastavro
        
        schema_id = self._ensure_schema_registered()
        parsed_schema = self._get_parsed_schema()
        
        # Create buffer with Confluent wire format header
        buffer = io.BytesIO()
        buffer.write(struct.pack('>bI', self.MAGIC_BYTE, schema_id))
        
        # Write Avro data
        fastavro.schemaless_writer(buffer, parsed_schema, data)
        
        return buffer.getvalue()
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """
        Deserialize Avro data with Confluent wire format.
        
        Args:
            data: Serialized bytes
            
        Returns:
            Deserialized dictionary
        """
        import fastavro
        
        buffer = io.BytesIO(data)
        
        # Read and validate magic byte
        magic, schema_id = struct.unpack('>bI', buffer.read(5))
        if magic != self.MAGIC_BYTE:
            raise ValueError(f"Invalid magic byte: {magic}")
        
        # Get schema from registry
        schema = self.registry.get_schema(schema_id)
        parsed_schema = fastavro.parse_schema(schema)
        
        # Read Avro data
        return fastavro.schemaless_reader(buffer, parsed_schema)


def create_avro_serializer(
    url: str, 
    api_key: str, 
    api_secret: str,
    subject: str = "enterprise-action-events-value"
) -> Optional[AvroSerializer]:
    """
    Create an Avro serializer for enterprise action events.
    
    Args:
        url: Schema Registry URL
        api_key: API key
        api_secret: API secret
        subject: Subject name for schema
        
    Returns:
        AvroSerializer or None if connection fails
    """
    try:
        client = SchemaRegistryClient(url, api_key, api_secret)
        if not client.check_connection():
            return None
        return AvroSerializer(client, ENTERPRISE_ACTION_EVENT_SCHEMA, subject)
    except Exception:
        return None
