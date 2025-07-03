
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sys
import os
import json
from typing import Dict, Any, Optional

# Add paths for our integrations
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(dashboard_dir)
sys.path.insert(0, parent_dir)  # For extropy_engine_mvp.py
sys.path.insert(0, os.path.join(parent_dir, "signalflow", "src"))  # For merchantflow.py

app = FastAPI(title="Emergent Systems Dashboard", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class XPMintRequest(BaseModel):
    delta_s: float
    c_l: float
    event_data: Dict[str, Any] = {}
    is_gaming: bool = False
    use_expanded: bool = False
    r: float = 1.0
    f: float = 1.0
    w: float = 1.0
    e: float = 1.0
    ts: float = 0.5

class MerchantRequest(BaseModel):
    name: str
    business_type: str
    monthly_cc_spend: float

class TransactionRequest(BaseModel):
    merchant_id: str
    amount: float
    customer_data: Optional[Dict[str, Any]] = None

@app.get("/")
async def read_root():
    return {
        "message": "Emergent Systems Dashboard Backend",
        "version": "1.0.0",
        "features": [
            "Extropy Engine XP Minting",
            "MerchantFlow CRM Integration", 
            "SignalFlow Task Management",
            "Real-time System Monitoring"
        ]
    }

@app.get("/status")
async def system_status():
    """Get overall system status"""
    try:
        # Test imports
        from extropy_engine_mvp import mint_xp
        from merchantflow import MerchantFlowCRM
        
        return {
            "status": "operational",
            "modules": {
                "extropy_engine": "available",
                "merchantflow": "available", 
                "signalflow": "available"
            },
            "timestamp": "2025-07-03T00:00:00Z"
        }
    except ImportError as e:
        return {
            "status": "degraded",
            "error": f"Module import error: {str(e)}",
            "modules": {
                "extropy_engine": "error",
                "merchantflow": "error",
                "signalflow": "unknown"
            }
        }

@app.post("/extropy/mint")
async def mint_xp_endpoint(request: XPMintRequest):
    """Mint Extropy Points using the core engine"""
    try:
        from extropy_engine_mvp import mint_xp
        
        xp_minted = mint_xp(
            delta_s=request.delta_s,
            c_l=request.c_l,
            event_data=request.event_data,
            is_gaming=request.is_gaming,
            use_expanded_formula=request.use_expanded,
            r=request.r, f=request.f, w=request.w, e=request.e, ts=request.ts
        )
        
        return {
            "success": True,
            "xp_minted": xp_minted,
            "parameters": request.dict(),
            "message": f"Successfully minted {xp_minted:.4f} XP" if xp_minted > 0 else "XP minting failed or resulted in 0 XP"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XP minting error: {str(e)}")

@app.post("/merchantflow/register")
async def register_merchant(request: MerchantRequest):
    """Register a new merchant in MerchantFlow"""
    try:
        from merchantflow import MerchantFlowCRM
        
        crm = MerchantFlowCRM()
        merchant_id = crm.register_merchant(
            name=request.name,
            business_type=request.business_type,
            monthly_cc_spend=request.monthly_cc_spend
        )
        
        return {
            "success": True,
            "merchant_id": merchant_id,
            "estimated_monthly_savings": request.monthly_cc_spend * 0.025,
            "message": f"Merchant '{request.name}' registered successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merchant registration error: {str(e)}")

@app.post("/merchantflow/transaction")
async def process_transaction(request: TransactionRequest):
    """Process a local transaction through MerchantFlow"""
    try:
        from merchantflow import MerchantFlowCRM
        
        crm = MerchantFlowCRM()
        # Setup a demo coral device if none exists
        if not crm.coral_device:
            crm.setup_coral_device(request.merchant_id, "demo_coral_device")
            
        result = crm.process_local_transaction(
            merchant_id=request.merchant_id,
            amount=request.amount,
            customer_data=request.customer_data or {"type": "dashboard_demo"}
        )
        
        return {
            "success": result.get("success", False),
            "transaction_data": result,
            "message": "Transaction processed successfully" if result.get("success") else result.get("error", "Transaction failed")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transaction processing error: {str(e)}")

@app.get("/merchantflow/report/{merchant_id}")
async def get_merchant_report(merchant_id: str):
    """Get entropy reduction report for a merchant"""
    try:
        from merchantflow import MerchantFlowCRM
        
        crm = MerchantFlowCRM()
        report = crm.get_daily_entropy_report(merchant_id)
        
        return {
            "success": True,
            "report": report,
            "message": "Report generated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")

@app.get("/simulate")
async def run_simulation():
    """Run an integrated simulation of all systems"""
    try:
        from extropy_engine_mvp import mint_xp
        from merchantflow import MerchantFlowCRM
        
        simulation_results = []
        
        # 1. Create a demo merchant
        crm = MerchantFlowCRM()
        merchant_id = crm.register_merchant(
            name="Demo Simulation Merchant",
            business_type="Technology",
            monthly_cc_spend=5000
        )
        simulation_results.append(f"✅ Registered merchant: {merchant_id}")
        
        # 2. Setup Coral device
        crm.setup_coral_device(merchant_id, "sim_coral_001")
        simulation_results.append("🧠 Coral device connected")
        
        # 3. Process demo transactions
        demo_transactions = [25.99, 45.67, 12.50, 78.90]
        total_xp = 0
        total_saved = 0
        
        for amount in demo_transactions:
            result = crm.process_local_transaction(merchant_id, amount)
            if result.get("success"):
                total_xp += result["xp_generated"]
                total_saved += result["cc_fee_saved"]
                simulation_results.append(f"💳 ${amount} → XP: {result['xp_generated']:.2f}")
        
        # 4. Test direct XP minting
        xp_direct = mint_xp(
            delta_s=15.0,
            c_l=2.0,
            event_data={"description": "Simulation entropy reduction", "simulation": True},
            is_gaming=False
        )
        simulation_results.append(f"🔥 Direct XP minted: {xp_direct:.4f}")
        
        # 5. Generate report
        report = crm.get_daily_entropy_report(merchant_id)
        
        return {
            "status": "Simulation completed successfully",
            "results": simulation_results,
            "summary": {
                "merchant_id": merchant_id,
                "total_xp_generated": total_xp,
                "total_cc_fees_saved": total_saved,
                "direct_xp_minted": xp_direct,
                "efficiency_score": report.get("efficiency_score", 0)
            },
            "report": report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
