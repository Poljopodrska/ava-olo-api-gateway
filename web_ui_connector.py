"""
Web UI Connector - Connects existing UI to new modular architecture
Maintains compatibility with current form.html interface
"""
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging
import os
import sys
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize FastAPI app for UI
app = FastAPI(
    title="AVA OLO Web Interface",
    description="Web UI for AVA OLO Agricultural Assistant",
    version="2.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API Gateway URL
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

class UIConnector:
    """Connects UI to API Gateway"""
    
    def __init__(self, api_url: str = API_GATEWAY_URL):
        self.api_url = api_url
        self.timeout = 30
        
    async def process_query(self, query: str, farmer_id: Optional[int] = None) -> Dict[str, Any]:
        """Send query to API Gateway"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/query",
                    json={
                        "query": query,
                        "farmer_id": farmer_id,
                        "context": {}
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"API error: {response.status_code}")
                    return {
                        "success": False,
                        "answer": "Oprosti, dogodila se greška. Molim pokušaj ponovno.",
                        "error": f"API error: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Query processing error: {str(e)}")
            return {
                "success": False,
                "answer": "Servis je trenutno nedostupan. Molim pokušaj kasnije.",
                "error": str(e)
            }

# Initialize connector
connector = UIConnector()

# Routes for existing UI
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page with form"""
    return templates.TemplateResponse("form.html", {
        "request": request,
        "response": None
    })

@app.post("/", response_class=HTMLResponse)
async def process_form(request: Request, question: str = Form(...)):
    """Process form submission"""
    logger.info(f"Form submission: {question}")
    
    # Process through API Gateway
    result = await connector.process_query(question)
    
    # Format response for template
    response_text = result.get("answer", "No response")
    
    # Add metadata if available
    if result.get("success") and result.get("metadata"):
        metadata = result["metadata"]
        if metadata.get("language") != "hr":
            response_text += f"\n\n[Detected language: {metadata.get('language')}]"
    
    return templates.TemplateResponse("form.html", {
        "request": request,
        "response": response_text,
        "question": question
    })

# API endpoint for JSON requests
@app.post("/ask")
async def ask_api(request: Request):
    """JSON API endpoint"""
    try:
        data = await request.json()
        question = data.get("question", "")
        farmer_id = data.get("farmer_id")
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        
        result = await connector.process_query(question, farmer_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard route
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Dashboard API endpoints
@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        async with httpx.AsyncClient() as client:
            # Get health status
            health_response = await client.get(f"{API_GATEWAY_URL}/api/v1/health")
            health = health_response.json() if health_response.status_code == 200 else {"status": "unknown"}
            
            return {
                "system_health": health.get("status", "unknown"),
                "total_queries": 0,  # Would come from monitoring
                "active_farmers": 0,  # Would come from database
                "response_time_avg": 0  # Would come from monitoring
            }
            
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return {"error": str(e)}

# Field management UI endpoints
@app.get("/fields", response_class=HTMLResponse)
async def fields_page(request: Request):
    """Fields management page"""
    return templates.TemplateResponse("fields.html", {"request": request})

@app.get("/fields/api/{farmer_id}")
async def get_fields_api(farmer_id: int):
    """Get fields for farmer"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_GATEWAY_URL}/api/v1/fields/{farmer_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Get fields error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Weather widget
@app.get("/weather/{location}")
async def get_weather_widget(location: str):
    """Get weather for UI widget"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_GATEWAY_URL}/api/v1/weather/{location}")
            return response.json()
    except Exception as e:
        logger.error(f"Weather widget error: {str(e)}")
        return {"error": str(e)}

# Test endpoint
@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify UI is running"""
    return {
        "status": "ok",
        "message": "AVA OLO Web UI is running",
        "api_gateway": API_GATEWAY_URL
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return templates.TemplateResponse("404.html", {
        "request": request,
        "message": "Stranica nije pronađena"
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors"""
    return templates.TemplateResponse("500.html", {
        "request": request,
        "message": "Dogodila se greška na serveru"
    }, status_code=500)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("AVA OLO Web UI starting...")
    
    # Check API Gateway connection
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_GATEWAY_URL}/api/v1/health")
            if response.status_code == 200:
                logger.info("API Gateway connection successful")
            else:
                logger.warning(f"API Gateway returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to connect to API Gateway: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("AVA OLO Web UI shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)