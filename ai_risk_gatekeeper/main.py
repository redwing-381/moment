"""
Main entry point for the AI Risk Gatekeeper system.

This module provides system orchestration, starting all agents
and managing the complete event processing pipeline.
"""

import asyncio
import logging
import sys
import signal
from typing import Optional

from ai_risk_gatekeeper.config.settings import config_manager
from ai_risk_gatekeeper.infrastructure import setup_kafka_infrastructure
from ai_risk_gatekeeper.agents import (
    EventProducer,
    SignalProcessor,
    DecisionAgent,
    ActionAgent,
    BehaviorPattern,
    create_event_producer,
    create_signal_processor,
    create_decision_agent,
    create_action_agent,
)


logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Set up structured logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def verify_connectivity() -> bool:
    """Verify connectivity to external services."""
    try:
        config = config_manager.load_config()
        config_manager.validate_config()
        logger.info("Configuration validated")
        
        # Verify Kafka infrastructure
        if not setup_kafka_infrastructure():
            logger.error("Kafka infrastructure verification failed")
            return False
        
        logger.info("All connectivity checks passed")
        return True
    except Exception as e:
        logger.error(f"Connectivity verification failed: {e}")
        return False


def run_demo(scenario: str = "mixed", num_events: int = 5) -> None:
    """
    Run a demonstration of the system.
    
    Args:
        scenario: Type of demo ("normal", "suspicious", "mixed")
        num_events: Number of events to generate
    """
    setup_logging("INFO")
    logger.info("=" * 60)
    logger.info("AI Risk Gatekeeper - Demo Mode")
    logger.info("=" * 60)
    
    # Create producer
    producer = create_event_producer()
    
    try:
        if scenario == "normal":
            patterns = [BehaviorPattern.NORMAL] * num_events
        elif scenario == "suspicious":
            patterns = [
                BehaviorPattern.HIGH_FREQUENCY,
                BehaviorPattern.GEO_ANOMALY,
                BehaviorPattern.PRIVILEGE_ESCALATION,
                BehaviorPattern.SUSPICIOUS,
                BehaviorPattern.HIGH_FREQUENCY,
            ][:num_events]
        else:  # mixed
            patterns = [
                BehaviorPattern.NORMAL,
                BehaviorPattern.NORMAL,
                BehaviorPattern.HIGH_FREQUENCY,
                BehaviorPattern.NORMAL,
                BehaviorPattern.GEO_ANOMALY,
            ][:num_events]
        
        logger.info(f"Generating {len(patterns)} events...")
        
        for i, pattern in enumerate(patterns, 1):
            event, time_ms = producer.generate_and_publish(pattern)
            logger.info(
                f"[{i}/{len(patterns)}] Published: actor={event.actor_id} "
                f"action={event.action} freq={event.frequency_last_60s} "
                f"geo_change={event.geo_change} ({time_ms:.2f}ms)"
            )
        
        producer.flush(timeout=10)
        logger.info(f"Demo complete. Stats: {producer.stats}")
        
    finally:
        producer.disconnect()


async def main() -> None:
    """Main application entry point."""
    setup_logging("INFO")
    
    logger.info("=" * 60)
    logger.info("Starting AI Risk Gatekeeper System")
    logger.info("=" * 60)
    
    # Verify connectivity
    if not await verify_connectivity():
        logger.error("Startup validation failed")
        sys.exit(1)
    
    logger.info("System ready. Use run_demo() to generate events.")
    logger.info("Press Ctrl+C to stop.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    
    logger.info("AI Risk Gatekeeper stopped")


if __name__ == "__main__":
    asyncio.run(main())
