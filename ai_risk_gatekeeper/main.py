"""
AI Risk Gatekeeper - Main Entry Point

Simple entry point for the package. For demos and real-time mode,
use the scripts in the project root:
- hackathon_demo.py  - Interactive demo for presentations
- run_realtime.py    - Real-time processing mode
"""

import asyncio
import logging
import sys

from ai_risk_gatekeeper.config.settings import config_manager
from ai_risk_gatekeeper.infrastructure import setup_kafka_infrastructure


def setup_logging(level: str = "INFO"):
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def verify_setup() -> bool:
    """Verify system configuration and connectivity."""
    try:
        config_manager.validate_config()
        return setup_kafka_infrastructure()
    except Exception as e:
        logging.error(f"Setup verification failed: {e}")
        return False


async def main():
    """Main entry point."""
    setup_logging()
    
    print("AI Risk Gatekeeper")
    print("=" * 40)
    
    if await verify_setup():
        print("✓ Configuration valid")
        print("✓ Kafka connected")
        print("\nRun one of:")
        print("  python hackathon_demo.py  - Interactive demo")
        print("  python run_realtime.py    - Real-time mode")
    else:
        print("✗ Setup verification failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
