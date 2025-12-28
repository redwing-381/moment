"""
AI Risk Gatekeeper - Web Application Entry Point

This is the main entry point for the FastAPI application.
The application is modularized in ai_risk_gatekeeper/web/.
"""

from dotenv import load_dotenv

load_dotenv()

from ai_risk_gatekeeper.web import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
