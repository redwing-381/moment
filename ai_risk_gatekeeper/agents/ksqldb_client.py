"""
ksqlDB client for Confluent Cloud.

Provides real-time stream processing queries for user risk analytics.
"""

import aiohttp
import base64
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


# ksqlDB DDL statements for stream and table creation
KSQL_CREATE_STREAM = """
CREATE STREAM IF NOT EXISTS action_events (
    event_id VARCHAR,
    actor_id VARCHAR,
    action VARCHAR,
    role VARCHAR,
    frequency_last_60s INT,
    geo_change BOOLEAN,
    timestamp VARCHAR,
    session_id VARCHAR,
    resource_sensitivity VARCHAR,
    risk_score DOUBLE
) WITH (
    KAFKA_TOPIC='enterprise-action-events',
    VALUE_FORMAT='JSON'
);
"""

KSQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS user_risk_summary AS
SELECT
    actor_id,
    WINDOWSTART AS window_start,
    WINDOWEND AS window_end,
    COUNT(*) AS event_count,
    AVG(risk_score) AS avg_risk,
    MAX(risk_score) AS max_risk,
    SUM(CASE WHEN risk_score > 0.7 THEN 1 ELSE 0 END) AS high_risk_count
FROM action_events
WINDOW TUMBLING (SIZE 5 MINUTES)
GROUP BY actor_id
EMIT CHANGES;
"""


@dataclass
class UserRiskSummary:
    """Windowed aggregation of user risk metrics."""
    actor_id: str
    window_start: datetime
    window_end: datetime
    event_count: int
    avg_risk: float
    max_risk: float
    high_risk_count: int
    
    @property
    def is_flagged(self) -> bool:
        """Check if user should be flagged as high-risk."""
        return (
            self.high_risk_count >= 3 or
            self.max_risk > 0.85 or
            (self.avg_risk > 0.6 and self.event_count > 5)
        )
    
    @classmethod
    def from_ksql_row(cls, row: List[Any]) -> 'UserRiskSummary':
        """
        Parse a ksqlDB result row into UserRiskSummary.
        
        Expected row format: [actor_id, window_start, window_end, event_count, avg_risk, max_risk, high_risk_count]
        """
        return cls(
            actor_id=row[0],
            window_start=datetime.fromtimestamp(row[1] / 1000) if row[1] else datetime.now(),
            window_end=datetime.fromtimestamp(row[2] / 1000) if row[2] else datetime.now(),
            event_count=int(row[3]) if row[3] else 0,
            avg_risk=float(row[4]) if row[4] else 0.0,
            max_risk=float(row[5]) if row[5] else 0.0,
            high_risk_count=int(row[6]) if row[6] else 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "actor_id": self.actor_id,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "event_count": self.event_count,
            "avg_risk": round(self.avg_risk, 3),
            "max_risk": round(self.max_risk, 3),
            "high_risk_count": self.high_risk_count,
            "is_flagged": self.is_flagged
        }


class KsqlDBClient:
    """Async client for Confluent ksqlDB."""
    
    def __init__(self, endpoint: str, api_key: str, api_secret: str):
        """
        Initialize ksqlDB client.
        
        Args:
            endpoint: ksqlDB endpoint URL
            api_key: API key for authentication
            api_secret: API secret for authentication
        """
        self.endpoint = endpoint.rstrip('/')
        self._auth_header = self._create_auth_header(api_key, api_secret)
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False
    
    def _create_auth_header(self, api_key: str, api_secret: str) -> str:
        """Create Basic auth header."""
        credentials = f"{api_key}:{api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/vnd.ksql.v1+json"
                }
            )
        return self._session
    
    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._connected = False
    
    async def execute_statement(self, statement: str) -> Dict[str, Any]:
        """
        Execute a ksqlDB DDL statement.
        
        Args:
            statement: ksqlDB statement (CREATE, DROP, etc.)
            
        Returns:
            Response from ksqlDB
        """
        session = await self._get_session()
        url = f"{self.endpoint}/ksql"
        
        payload = {
            "ksql": statement,
            "streamsProperties": {}
        }
        
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                self._connected = True
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"ksqlDB error ({response.status}): {text}")
    
    async def pull_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a pull query for point-in-time results.
        
        Args:
            query: SELECT query
            
        Returns:
            List of result rows
        """
        session = await self._get_session()
        url = f"{self.endpoint}/query"
        
        payload = {
            "ksql": query,
            "streamsProperties": {}
        }
        
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                self._connected = True
                results = []
                async for line in response.content:
                    if line.strip():
                        import json
                        try:
                            data = json.loads(line.decode())
                            if isinstance(data, list):
                                results.extend(data)
                            elif isinstance(data, dict) and 'row' in data:
                                results.append(data['row']['columns'])
                        except json.JSONDecodeError:
                            continue
                return results
            else:
                text = await response.text()
                raise Exception(f"ksqlDB query error ({response.status}): {text}")
    
    async def get_user_risk_summaries(self, limit: int = 10) -> List[UserRiskSummary]:
        """
        Get user risk summaries from ksqlDB.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of UserRiskSummary objects
        """
        query = f"""
        SELECT actor_id, window_start, window_end, event_count, avg_risk, max_risk, high_risk_count
        FROM user_risk_summary
        LIMIT {limit};
        """
        
        try:
            results = await self.pull_query(query)
            summaries = []
            for row in results:
                if isinstance(row, list) and len(row) >= 7:
                    try:
                        summaries.append(UserRiskSummary.from_ksql_row(row))
                    except Exception:
                        continue
            return summaries
        except Exception as e:
            # Return empty list on error - graceful degradation
            return []
    
    async def check_connection(self) -> bool:
        """Check if ksqlDB is reachable."""
        try:
            session = await self._get_session()
            url = f"{self.endpoint}/info"
            async with session.get(url) as response:
                self._connected = response.status == 200
                return self._connected
        except Exception:
            self._connected = False
            return False
    
    async def setup_streams(self) -> bool:
        """
        Set up required streams and tables.
        
        Returns:
            True if setup successful
        """
        try:
            await self.execute_statement(KSQL_CREATE_STREAM)
            await self.execute_statement(KSQL_CREATE_TABLE)
            return True
        except Exception as e:
            # Streams may already exist - that's OK
            if "already exists" in str(e).lower():
                return True
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected


async def create_ksqldb_client(
    endpoint: str,
    api_key: str,
    api_secret: str
) -> Optional[KsqlDBClient]:
    """
    Create and verify a ksqlDB client connection.
    
    Args:
        endpoint: ksqlDB endpoint URL
        api_key: API key
        api_secret: API secret
        
    Returns:
        KsqlDBClient or None if connection fails
    """
    client = KsqlDBClient(endpoint, api_key, api_secret)
    if await client.check_connection():
        return client
    return None
