#!/usr/bin/env python3
"""
Master Control Hub for Extropy Ecosystem
Unified dashboard integrating all services through the API Gateway
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import asyncio
import aiohttp
import json
import os
import logging
from datetime import datetime
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Extropy Master Control Hub",
    description="Unified dashboard for physics-based coordination ecosystem",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Security
security = HTTPBearer()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "https://xpengine.org",
        "https://*.xpengine.org"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service configuration
SERVICES = {
    "gateway": os.getenv("GATEWAY_URL", "http://localhost:3000"),
    "auth": os.getenv("AUTH_URL", "http://localhost:3002"),
    "xp_ledger": os.getenv("XP_LEDGER_URL", "http://localhost:3001"),
    "signalflow": os.getenv("SIGNALFLOW_URL", "http://localhost:3003"),
    "levelup": os.getenv("LEVELUP_URL", "http://localhost:3004"),
    "homeflow": os.getenv("HOMEFLOW_URL", "http://localhost:3005")
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str = None):
        self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                await connection.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Request models
class XPMintRequest(BaseModel):
    user_id: str
    platform: str
    action_type: str
    action_description: str
    entropy_delta: float
    causal_closure_speed: float
    domain: str
    metadata: Optional[Dict[str, Any]] = {}

class UserSyncRequest(BaseModel):
    user_id: str
    platforms: Optional[List[str]] = None
    force_sync: bool = False

class TokenConversionRequest(BaseModel):
    user_id: str
    xp_amount: float

class PlatformConnectionRequest(BaseModel):
    user_id: str
    platform: str
    credentials: Optional[Dict[str, Any]] = {}

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{SERVICES['auth']}/api/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return user_data["user"]
                else:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# Root endpoint
@app.get("/")
async def read_root():
    return {
        "service": "Extropy Master Control Hub",
        "description": "Unified dashboard for physics-based coordination ecosystem",
        "version": "2.0.0",
        "features": [
            "Unified XP Tracking Across All Platforms",
            "Real-time Dashboard with Live Updates", 
            "Cross-platform User Management",
            "Contribution Token Economy",
            "Loop Closure and Retroactive XP",
            "Advanced Analytics and Insights",
            "Platform Integration and Sync"
        ],
        "ecosystem": {
            "total_platforms": len(SERVICES) - 1,  # Exclude gateway
            "physics_formula": "XP = ΔS / c_L²",
            "domain": "xpengine.org"
        }
    }

# Health check for all services
@app.get("/api/health")
async def health_check():
    service_health = {}
    
    async with aiohttp.ClientSession() as session:
        for service_name, service_url in SERVICES.items():
            try:
                async with session.get(f"{service_url}/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        service_health[service_name] = {
                            "status": "healthy",
                            "uptime": data.get("uptime", 0),
                            "response_time": "< 5s"
                        }
                    else:
                        service_health[service_name] = {
                            "status": "degraded",
                            "error": f"HTTP {response.status}"
                        }
            except Exception as e:
                service_health[service_name] = {
                    "status": "unhealthy", 
                    "error": str(e)
                }
    
    overall_status = "healthy" if all(
        s["status"] == "healthy" for s in service_health.values()
    ) else "degraded"
    
    return {
        "overall_status": overall_status,
        "services": service_health,
        "timestamp": datetime.now().isoformat(),
        "ecosystem_health": calculate_ecosystem_health(service_health)
    }

# Ecosystem overview
@app.get("/api/ecosystem/overview")
async def ecosystem_overview(current_user = Depends(get_current_user)):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
        
        try:
            # Get ecosystem analytics from XP Ledger
            async with session.get(f"{SERVICES['xp_ledger']}/api/analytics/ecosystem", headers=headers) as response:
                ecosystem_data = await response.json() if response.status == 200 else {}
            
            # Get user's personal stats
            async with session.get(f"{SERVICES['xp_ledger']}/api/analytics/user/{current_user['userId']}", headers=headers) as response:
                user_stats = await response.json() if response.status == 200 else {}
            
            # Get platform connections
            async with session.get(f"{SERVICES['auth']}/api/platforms/connected", headers=headers) as response:
                platforms = await response.json() if response.status == 200 else {}
            
            return {
                "user": {
                    "userId": current_user["userId"],
                    "email": current_user["email"],
                    "totalXP": user_stats.get("user", {}).get("totalXP", 0),
                    "contributionTokens": user_stats.get("user", {}).get("contributionTokens", 0),
                    "rank": user_stats.get("user", {}).get("rank", 0),
                    "connectedPlatforms": platforms.get("connectedPlatforms", [])
                },
                "ecosystem": {
                    "totalUsers": ecosystem_data.get("ecosystem", {}).get("totalUsers", 0),
                    "totalXP": ecosystem_data.get("ecosystem", {}).get("totalXP", 0),
                    "activeUsers": ecosystem_data.get("ecosystem", {}).get("activeUsers", 0),
                    "totalTransactions": ecosystem_data.get("ecosystem", {}).get("totalTransactions", 0),
                    "platformActivity": ecosystem_data.get("platformActivity", []),
                    "domainDistribution": ecosystem_data.get("domainDistribution", [])
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ecosystem overview error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get ecosystem overview: {str(e)}")

# XP minting through unified system
@app.post("/api/xp/mint")
async def mint_xp(request: XPMintRequest, current_user = Depends(get_current_user)):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
        
        try:
            payload = {
                "userId": request.user_id,
                "platform": request.platform,
                "actionType": request.action_type,
                "actionDescription": request.action_description,
                "entropyDelta": request.entropy_delta,
                "causalClosureSpeed": request.causal_closure_speed,
                "domain": request.domain,
                "validators": [
                    {
                        "type": "human",
                        "validatorId": current_user["userId"],
                        "score": 0.95,
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "metadata": {
                    **request.metadata,
                    "source": "master_control_hub",
                    "user_initiated": True
                }
            }
            
            async with session.post(
                f"{SERVICES['xp_ledger']}/api/xp/transaction", 
                json=payload,
                headers=headers
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    
                    # Broadcast XP update
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "xp_minted",
                            "data": result,
                            "timestamp": datetime.now().isoformat()
                        }),
                        request.user_id
                    )
                    
                    return result
                else:
                    error_data = await response.json()
                    raise HTTPException(status_code=response.status, detail=error_data.get("error", "XP minting failed"))
                    
        except Exception as e:
            logger.error(f"XP minting error: {e}")
            raise HTTPException(status_code=500, detail=f"XP minting failed: {str(e)}")

# User synchronization
@app.post("/api/sync/user")
async def sync_user(request: UserSyncRequest, current_user = Depends(get_current_user)):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
        
        try:
            # Sync user data across platforms
            sync_payload = {
                "platforms": request.platforms or ["signalflow", "levelup", "homeflow", "xp-ledger"]
            }
            
            async with session.post(
                f"{SERVICES['gateway']}/api/sync/user/{request.user_id}",
                json=sync_payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Sync XP data
                    async with session.post(
                        f"{SERVICES['gateway']}/api/sync/xp/{request.user_id}",
                        json={"forceSync": request.force_sync},
                        headers=headers
                    ) as xp_response:
                        if xp_response.status == 200:
                            xp_result = await xp_response.json()
                            result["xpSync"] = xp_result
                    
                    return result
                else:
                    error_data = await response.json()
                    raise HTTPException(status_code=response.status, detail=error_data.get("error", "Sync failed"))
                    
        except Exception as e:
            logger.error(f"User sync error: {e}")
            raise HTTPException(status_code=500, detail=f"User sync failed: {str(e)}")

# Token conversion
@app.post("/api/tokens/convert")
async def convert_tokens(request: TokenConversionRequest, current_user = Depends(get_current_user)):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
        
        try:
            payload = {
                "userId": request.user_id,
                "xpAmount": request.xp_amount
            }
            
            async with session.post(
                f"{SERVICES['xp_ledger']}/api/tokens/convert",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Broadcast token update
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "tokens_converted",
                            "data": result,
                            "timestamp": datetime.now().isoformat()
                        }),
                        request.user_id
                    )
                    
                    return result
                else:
                    error_data = await response.json()
                    raise HTTPException(status_code=response.status, detail=error_data.get("error", "Token conversion failed"))
                    
        except Exception as e:
            logger.error(f"Token conversion error: {e}")
            raise HTTPException(status_code=500, detail=f"Token conversion failed: {str(e)}")

# Platform connection
@app.post("/api/platforms/connect")
async def connect_platform(request: PlatformConnectionRequest, current_user = Depends(get_current_user)):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
        
        try:
            payload = {
                "platformUserId": request.user_id,
                "username": current_user.get("profile", {}).get("displayName", ""),
                "credentials": request.credentials
            }
            
            async with session.post(
                f"{SERVICES['auth']}/api/platforms/connect/{request.platform}",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Broadcast platform connection
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "platform_connected",
                            "data": result,
                            "timestamp": datetime.now().isoformat()
                        }),
                        request.user_id
                    )
                    
                    return result
                else:
                    error_data = await response.json()
                    raise HTTPException(status_code=response.status, detail=error_data.get("error", "Platform connection failed"))
                    
        except Exception as e:
            logger.error(f"Platform connection error: {e}")
            raise HTTPException(status_code=500, detail=f"Platform connection failed: {str(e)}")

# Real-time analytics
@app.get("/api/analytics/realtime")
async def realtime_analytics(current_user = Depends(get_current_user)):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {current_user.get('token', '')}"}
        
        try:
            # Get real-time data from multiple sources
            analytics_data = {}
            
            # XP Ledger analytics
            async with session.get(f"{SERVICES['xp_ledger']}/api/analytics/ecosystem?timeframe=24h", headers=headers) as response:
                if response.status == 200:
                    analytics_data["xp_ledger"] = await response.json()
            
            # User's personal analytics
            async with session.get(f"{SERVICES['xp_ledger']}/api/analytics/user/{current_user['userId']}?timeframe=24h", headers=headers) as response:
                if response.status == 200:
                    analytics_data["user_analytics"] = await response.json()
            
            # Platform-specific analytics
            for platform in ["signalflow", "levelup", "homeflow"]:
                async with session.get(f"{SERVICES['xp_ledger']}/api/analytics/platform/{platform}?timeframe=24h", headers=headers) as response:
                    if response.status == 200:
                        analytics_data[f"{platform}_analytics"] = await response.json()
            
            return {
                "analytics": analytics_data,
                "timestamp": datetime.now().isoformat(),
                "updateInterval": "30s"
            }
            
        except Exception as e:
            logger.error(f"Real-time analytics error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get real-time analytics: {str(e)}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Connected to Master Control Hub",
            "userId": user_id,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            elif message.get("type") == "subscribe":
                # Subscribe to specific update types
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "subscription": message.get("subscription"),
                    "timestamp": datetime.now().isoformat()
                }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} disconnected from WebSocket")

# Proxy endpoints for platform-specific operations
@app.get("/api/platform/{platform}/status")
async def get_platform_status(platform: str, current_user = Depends(get_current_user)):
    if platform not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVICES[platform]}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "platform": platform,
                        "status": data,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(status_code=response.status, detail=f"Platform {platform} unavailable")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get platform status: {str(e)}")

# Helper functions
def calculate_ecosystem_health(service_health):
    healthy_services = sum(1 for s in service_health.values() if s["status"] == "healthy")
    total_services = len(service_health)
    
    health_percentage = (healthy_services / total_services) * 100 if total_services > 0 else 0
    
    if health_percentage >= 90:
        return {"status": "excellent", "percentage": health_percentage}
    elif health_percentage >= 70:
        return {"status": "good", "percentage": health_percentage}
    elif health_percentage >= 50:
        return {"status": "degraded", "percentage": health_percentage}
    else:
        return {"status": "critical", "percentage": health_percentage}

# Static file serving for frontend
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

@app.get("/manifest.json")
async def get_manifest():
    return FileResponse("frontend/build/manifest.json")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Serve React app for all non-API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    if os.path.exists(f"frontend/build/{full_path}"):
        return FileResponse(f"frontend/build/{full_path}")
    else:
        return FileResponse("frontend/build/index.html")

if __name__ == "__main__":
    uvicorn.run(
        "master-control-hub:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 3006)),
        reload=True,
        log_level="info"
    )