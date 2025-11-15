"""
Plane API Client for Kriya Backend
Handles communication with Plane backend on behalf of users
"""
import requests
import uuid
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from ..models import User
from ..config import get_settings
from ..crud import generate_jwt_token

settings = get_settings()


class PlaneClient:
    """Client for communicating with Plane backend on behalf of users"""
    
    def __init__(self, plane_base_url: str = None):
        self.base_url = (plane_base_url or settings.PLANE_BACKEND_URL).rstrip('/')
        self.service_api_key = settings.PLANE_API_KEY
        
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        user_api_token: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        session: Optional[requests.Session] = None
    ) -> Dict[Any, Any]:
        """Make authenticated request to Plane API"""
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-Api-Key": user_api_token,
            "Content-Type": "application/json"
        }
        
        client = session or requests
        try:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Safely get error message to avoid Unicode encoding issues
            try:
                error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            except (UnicodeEncodeError, UnicodeDecodeError):
                error_msg = f"{type(e).__name__}"
            print(f"Plane API Error: {error_msg}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    response_text = e.response.text.encode('ascii', 'ignore').decode('ascii')
                    print(f"Response: {response_text}")
                except:
                    print("Response: [Unable to decode response]")
            raise Exception(f"Failed to communicate with Plane: {error_msg}")
    
    def authenticate_user_with_plane(
        self,
        kriya_jwt_token: str
    ) -> requests.Session:
        """
        Authenticate with Plane using Kriya JWT token
        Creates Plane user account if it doesn't exist
        Returns: requests.Session with authenticated cookies
        """
        session = requests.Session()
        
        # Authenticate with Plane using Kriya token
        auth_url = f"{self.base_url}/api/auth/kriya/token/"
        response = session.post(
            auth_url,
            json={"token": kriya_jwt_token},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to authenticate with Plane: {response.status_code} - {response.text}")
        
        # Session now has authentication cookies
        return session
    
    def create_api_token_for_user(
        self,
        session: requests.Session,
        label: str = "Kriya Integration",
        description: str = "API token for Kriya service-to-service communication"
    ) -> Dict[str, Any]:
        """
        Create API token for authenticated user
        Requires authenticated session
        Returns: API token data including token string
        """
        token_url = f"{self.base_url}/api/users/me/api-tokens/"
        
        response = session.post(
            token_url,
            json={
                "label": label,
                "description": description
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create API token: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_user_info(self, session: requests.Session) -> Dict[str, Any]:
        """Get current user info from Plane"""
        user_url = f"{self.base_url}/api/users/me/"
        response = session.get(user_url, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.status_code}")
        
        return response.json()
    
    def get_or_create_user_token(
        self, 
        db: Session,
        kriya_user: User
    ) -> Tuple[str, str]:
        """
        Get or create user in Plane and return (plane_user_id, api_token)
        
        Flow:
        1. Check if user already has Plane API token (cached)
        2. If not, authenticate with Plane using Kriya JWT
        3. Create/get Plane user account
        4. Generate API token for that user
        5. Store token in Kriya database
        """
        
        # Check if we already have cached token
        if kriya_user.plane_api_token:
            # Validate token is still valid
            if self._validate_api_token(kriya_user.plane_api_token):
                return kriya_user.plane_user_id or "", kriya_user.plane_api_token
        
        # Generate Kriya JWT token for this user
        kriya_jwt, _ = generate_jwt_token(kriya_user)
        
        # Authenticate with Plane (creates user if needed)
        session = self.authenticate_user_with_plane(kriya_jwt)
        
        # Get user info to store Plane user ID
        try:
            user_info = self.get_user_info(session)
            plane_user_id = str(user_info.get("id", ""))
            plane_email = user_info.get("email", "")
        except Exception as e:
            print(f"Warning: Could not get user info: {e}")
            plane_user_id = ""
            plane_email = ""
        
        # Create API token for this user
        try:
            token_data = self.create_api_token_for_user(
                session,
                label=f"Kriya-{kriya_user.phone_number}",
                description=f"API token for Kriya user {kriya_user.phone_number}"
            )
            api_token = token_data.get("token", "")
            
            if not api_token:
                raise Exception("API token not returned from Plane")
        except Exception as e:
            # Safely get error message to avoid Unicode encoding issues
            try:
                error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            except (UnicodeEncodeError, UnicodeDecodeError):
                error_msg = f"{type(e).__name__}"
            print(f"Error creating API token: {error_msg}")
            # Fallback: Try to get existing tokens
            # For now, raise error - user needs to authenticate via dashboard first
            raise Exception(f"Failed to create API token. User may need to authenticate via dashboard first: {error_msg}")
        
        # Store in database
        kriya_user.plane_user_id = plane_user_id
        kriya_user.plane_api_token = api_token
        kriya_user.plane_email = plane_email or f"{kriya_user.phone_number.replace('+', '')}@kriya.local"
        
        # Set default workspace/project if not set
        if not kriya_user.plane_workspace_slug:
            kriya_user.plane_workspace_slug = settings.PLANE_WORKSPACE_SLUG
        if not kriya_user.plane_project_id:
            kriya_user.plane_project_id = settings.PLANE_PROJECT_ID
        
        db.commit()
        db.refresh(kriya_user)
        
        return plane_user_id, api_token
    
    def _validate_api_token(self, api_token: str) -> bool:
        """Check if API token is still valid"""
        try:
            response = requests.get(
                f"{self.base_url}/api/users/me/",
                headers={"X-Api-Key": api_token},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    # ===== Task Management APIs =====
    
    def create_task(
        self,
        user_api_token: str,
        workspace_slug: str,
        project_id: str,
        task_data: Dict
    ) -> Dict:
        """Create a task in Plane on behalf of user"""
        return self._make_request(
            method="POST",
            endpoint=f"/api/workspaces/{workspace_slug}/projects/{project_id}/issues/",
            user_api_token=user_api_token,
            data=task_data
        )
    
    def get_tasks(
        self,
        user_api_token: str,
        workspace_slug: str,
        project_id: str,
        filters: Optional[Dict] = None
    ) -> list[Dict]:
        """Get tasks from Plane on behalf of user"""
        response = self._make_request(
            method="GET",
            endpoint=f"/api/workspaces/{workspace_slug}/projects/{project_id}/issues/",
            user_api_token=user_api_token,
            params=filters
        )
        return response if isinstance(response, list) else response.get('results', [])
    
    def update_task(
        self,
        user_api_token: str,
        workspace_slug: str,
        project_id: str,
        issue_id: str,
        task_data: Dict
    ) -> Dict:
        """Update a task in Plane on behalf of user"""
        return self._make_request(
            method="PATCH",
            endpoint=f"/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
            user_api_token=user_api_token,
            data=task_data
        )
    
    def delete_task(
        self,
        user_api_token: str,
        workspace_slug: str,
        project_id: str,
        issue_id: str
    ) -> None:
        """Delete a task in Plane on behalf of user"""
        self._make_request(
            method="DELETE",
            endpoint=f"/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
            user_api_token=user_api_token
        )
    
    def proxy_request(
        self,
        user_api_token: str,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Any:
        """
        Proxy any Plane API request on behalf of user
        Used for API gateway functionality
        """
        # Ensure endpoint starts with /api
        if not endpoint.startswith('/api'):
            endpoint = f"/api{endpoint}" if not endpoint.startswith('/') else f"/api{endpoint}"
        
        return self._make_request(
            method=method,
            endpoint=endpoint,
            user_api_token=user_api_token,
            data=data,
            params=params
        )

