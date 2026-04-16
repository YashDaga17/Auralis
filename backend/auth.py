"""
Authentication and authorization middleware for multi-tenant isolation.
Extracts user_id and company_id from JWT tokens.
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

security = HTTPBearer(auto_error=False)


class AuthContext:
    """Authentication context extracted from JWT token."""
    def __init__(self, user_id: str, company_id: str, email: Optional[str] = None):
        self.user_id = user_id
        self.company_id = company_id
        self.email = email


async def get_auth_context(request: Request) -> Optional[AuthContext]:
    """
    Extract authentication context from JWT token.
    
    Returns:
        AuthContext with user_id and company_id, or None if auth is disabled
        
    Raises:
        HTTPException: If token is invalid, expired, or missing required claims
    """
    # Skip authentication if disabled (for development)
    if not AUTH_ENABLED:
        # Return default context for development
        return AuthContext(
            user_id="dev-user",
            company_id="00000000-0000-0000-0000-000000000000",
            email="dev@example.com"
        )
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        # Decode and verify JWT token
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        
        # Extract required claims
        user_id = payload.get("sub") or payload.get("user_id")
        company_id = payload.get("company_id") or payload.get("org_id")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' or 'user_id' claim",
            )
        
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'company_id' or 'org_id' claim",
            )
        
        return AuthContext(
            user_id=str(user_id),
            company_id=str(company_id),
            email=email
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_tenant_access(auth: AuthContext, resource_company_id: str) -> None:
    """
    Verify that the authenticated user has access to the requested resource.
    
    Args:
        auth: Authentication context with user's company_id
        resource_company_id: Company ID of the resource being accessed
        
    Raises:
        HTTPException: If user's company_id doesn't match resource company_id
    """
    if auth.company_id != resource_company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions for this resource",
        )
