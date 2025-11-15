"""
Plane API Proxy Router
Proxies all Plane API requests on behalf of authenticated Kriya users
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from ..database import get_db
from ..services.plane_client import PlaneClient
from .. import crud

router = APIRouter(prefix="/api/plane", tags=["Plane Proxy"])
plane_client = PlaneClient()


def get_current_user_from_token(
    authorization: Optional[str] = Header(None, alias="Authorization", description="Kriya JWT token: Bearer <token>"),
    x_kriya_token: Optional[str] = Header(None, alias="X-Kriya-Token", description="Alternative: Kriya JWT token"),
    db: Session = Depends(get_db)
):
    """Extract and validate user from Kriya JWT token"""
    # Get token from either Authorization header or X-Kriya-Token header
    token = None
    if authorization:
        # Remove "Bearer " prefix if present
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    elif x_kriya_token:
        token = x_kriya_token
    
    if not token:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required. Provide token via Authorization: Bearer <token> or X-Kriya-Token header"
        )
    
    user = crud.get_user_from_jwt(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_plane_request(
    path: str,
    request: Request,
    user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Proxy any Plane API request on behalf of authenticated user
    
    Headers:
    - Authorization: Bearer <kriya_jwt_token>
    
    The request will be forwarded to Plane with the user's API token.
    """
    try:
        # Get or create user's Plane API token
        plane_user_id, api_token = plane_client.get_or_create_user_token(db, user)
        
        if not api_token:
            raise HTTPException(
                status_code=500,
                detail="Failed to get Plane API token. Please try again."
            )
        
        # Get request method and data
        method = request.method
        endpoint = f"/{path}"
        
        # Get query parameters
        params = dict(request.query_params)
        
        # Get request body if present
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
            except:
                body = None
        
        # Make request to Plane on behalf of user
        response_data = plane_client.proxy_request(
            user_api_token=api_token,
            method=method,
            endpoint=endpoint,
            data=body,
            params=params if params else None
        )
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        # Sanitize error message to avoid Unicode encoding issues
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"Plane proxy error: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to proxy request to Plane: {error_msg}"
        )

