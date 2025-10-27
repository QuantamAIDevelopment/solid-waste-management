"""Authentication API endpoints for token management."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.services.auth_service import get_auth_service
from typing import Dict, Any

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.get("/token/info")
async def get_token_info():
    """Get information about the current authentication token."""
    try:
        auth_service = get_auth_service()
        token_info = auth_service.get_token_info()
        
        return JSONResponse({
            "status": "success",
            "data": token_info,
            "message": "Token information retrieved successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token info: {str(e)}")

@router.post("/token/refresh")
async def refresh_token():
    """Force refresh the authentication token."""
    try:
        auth_service = get_auth_service()
        success = auth_service.force_refresh()
        
        if success:
            token_info = auth_service.get_token_info()
            return JSONResponse({
                "status": "success",
                "data": token_info,
                "message": "Token refreshed successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh token")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")

@router.get("/status")
async def get_auth_status():
    """Get overall authentication status."""
    try:
        auth_service = get_auth_service()
        token_info = auth_service.get_token_info()
        
        status = {
            "authentication_enabled": True,
            "auto_refresh_enabled": True,
            "token_status": "valid" if token_info["is_valid"] else "invalid",
            "token_info": token_info
        }
        
        return JSONResponse({
            "status": "success",
            "data": status,
            "message": "Authentication status retrieved successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get auth status: {str(e)}")