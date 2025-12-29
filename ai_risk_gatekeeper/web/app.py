"""
FastAPI application factory for AI Risk Gatekeeper.

This module creates and configures the FastAPI application.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .state import state
from .routes import router
from .websocket import websocket_endpoint
from ai_risk_gatekeeper.agents import EventProducer, SignalProcessor, DecisionAgent
from ai_risk_gatekeeper.agents.hybrid_decision_engine import HybridDecisionEngine
from ai_risk_gatekeeper.config.settings import config_manager

# Optional Confluent advanced features
try:
    from ai_risk_gatekeeper.agents.schema_registry import SchemaRegistryClient
    from ai_risk_gatekeeper.agents.ksqldb_client import create_ksqldb_client
    from ai_risk_gatekeeper.agents.confluent_metrics import create_confluent_metrics_client
    CONFLUENT_FEATURES_AVAILABLE = True
except ImportError:
    CONFLUENT_FEATURES_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections on startup and cleanup on shutdown."""
    # Initialize core agents
    try:
        state.producer = EventProducer()
        state.producer.connect()
        state.kafka_metrics["connection_status"] = "connected"
        state.kafka_metrics["topics_used"].add("enterprise-action-events")
        
        # Disable real frequency tracking to avoid threading issues
        state.processor = SignalProcessor(use_real_frequency=False)
        state.decision_agent = DecisionAgent()
        state.decision_agent.connect()
        
        # Initialize hybrid decision engine for high-throughput processing
        state.hybrid_engine = HybridDecisionEngine(
            low_threshold=0.3,      # Auto-allow below this
            high_threshold=0.8,     # Auto-block above this
            max_concurrent_ai=10,   # Max concurrent AI requests
            max_queue_size=100,     # Queue overflow threshold
            cache_ttl_seconds=300,  # 5 minute cache TTL
            cache_max_size=1000     # Max cached decisions
        )
        print("✓ Core agents connected (with hybrid decision engine)")
    except Exception as e:
        state.kafka_metrics["connection_status"] = "error"
        print(f"Warning: Could not connect agents: {e}")
    
    # Initialize Confluent Advanced Features (graceful degradation)
    if CONFLUENT_FEATURES_AVAILABLE:
        await _init_confluent_features()
    
    yield
    
    # Cleanup
    await _cleanup()


async def _init_confluent_features():
    """Initialize Confluent Cloud advanced features."""
    try:
        config = config_manager.load_config()
        
        # Schema Registry
        if config.schema_registry:
            try:
                client = SchemaRegistryClient(
                    config.schema_registry.url,
                    config.schema_registry.api_key,
                    config.schema_registry.api_secret
                )
                if client.check_connection():
                    state.schema_registry_client = client
                    state.confluent_status["schema_registry"]["connected"] = True
                    state.confluent_status["schema_registry"]["format"] = "Avro"
                    print("✓ Schema Registry connected")
            except Exception as e:
                print(f"Schema Registry unavailable: {e}")
        
        # ksqlDB
        if config.ksqldb:
            try:
                client = await create_ksqldb_client(
                    config.ksqldb.endpoint,
                    config.ksqldb.api_key,
                    config.ksqldb.api_secret
                )
                if client:
                    state.ksqldb_client = client
                    state.confluent_status["ksqldb"]["connected"] = True
                    if await client.setup_streams():
                        state.confluent_status["ksqldb"]["streams_ready"] = True
                    print("✓ ksqlDB connected")
            except Exception as e:
                print(f"ksqlDB unavailable: {e}")
        
        # Confluent Cloud Metrics
        if config.confluent_cloud:
            try:
                client = await create_confluent_metrics_client(
                    config.confluent_cloud.api_key,
                    config.confluent_cloud.api_secret,
                    config.confluent_cloud.cluster_id,
                    config.confluent_cloud.environment_id
                )
                if client:
                    state.confluent_metrics_client = client
                    state.confluent_status["metrics_api"]["connected"] = True
                    state.confluent_status["metrics_api"]["cluster_id"] = config.confluent_cloud.cluster_id
                    print("✓ Confluent Metrics API connected")
            except Exception as e:
                print(f"Confluent Metrics API unavailable: {e}")
                
    except Exception as e:
        print(f"Confluent features initialization error: {e}")


async def _cleanup():
    """Cleanup resources on shutdown."""
    if state.producer:
        state.producer.disconnect()
    if state.decision_agent:
        state.decision_agent.disconnect()
    if state.ksqldb_client:
        await state.ksqldb_client.close()
    if state.confluent_metrics_client:
        await state.confluent_metrics_client.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="AI Risk Gatekeeper",
        description="Real-time AI-powered Enterprise Security",
        lifespan=lifespan
    )
    
    # Mount static files
    application.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Include routes
    application.include_router(router)
    
    # Add WebSocket endpoint
    application.websocket("/ws")(websocket_endpoint)
    
    return application


# Create the app instance
app = create_app()
