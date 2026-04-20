"""
API endpoints for user preferences management.

This module provides CRUD operations for user preferences including
communication style, preferred sources, and notification settings.

Requirements: 37.1, 37.2, 37.6
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import uuid

from database import get_db
from auth import get_auth_context, AuthContext
from models import UserPreference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


# ============================================================================
# Pydantic Models
# ============================================================================


class UserPreferenceCreate(BaseModel):
    """Request model for creating/updating user preferences."""
    user_id: str = Field(..., description="User identifier")
    agent_id: Optional[str] = Field(None, description="Optional agent-specific preferences")
    communication_style: Optional[str] = Field(
        'detailed',
        description="Communication style: 'concise', 'detailed', or 'technical'"
    )
    preferred_sources: Optional[List[str]] = Field(
        default_factory=list,
        description="List of preferred Qdrant collection names"
    )
    notification_preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Notification settings (email, SMS, in-app)"
    )


class UserPreferenceResponse(BaseModel):
    """Response model for user preferences."""
    user_id: str
    agent_id: Optional[str]
    communication_style: Optional[str]
    preferred_sources: Optional[List[str]]
    notification_preferences: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("", response_model=UserPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_preferences(
    preferences: UserPreferenceCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """
    Create or update user preferences.
    
    If preferences already exist for the user_id and agent_id combination,
    they will be updated. Otherwise, new preferences will be created.
    
    Requirements: 37.1, 37.6
    
    Args:
        preferences: User preference data
        db: Database session
        auth: Authentication context
        
    Returns:
        Created or updated user preferences
        
    Raises:
        HTTPException: If company_id is missing or validation fails
    """
    try:
        # Get company_id from auth context
        company_id = auth.company_id
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company_id is required in authentication context"
            )
        
        # Convert company_id string to UUID if needed
        if isinstance(company_id, str):
            company_id_uuid = uuid.UUID(company_id)
        else:
            company_id_uuid = company_id
        
        # Validate communication_style
        valid_styles = ['concise', 'detailed', 'technical']
        if preferences.communication_style and preferences.communication_style not in valid_styles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"communication_style must be one of: {', '.join(valid_styles)}"
            )
        
        logger.info(
            f"Creating/updating preferences for user {preferences.user_id}, "
            f"agent {preferences.agent_id}, company {company_id}"
        )
        
        # Check if preferences already exist
        query = db.query(UserPreference).filter(
            UserPreference.user_id == preferences.user_id,
            UserPreference.company_id == company_id_uuid
        )
        
        # Filter by agent_id if provided
        if preferences.agent_id:
            query = query.filter(UserPreference.agent_id == preferences.agent_id)
        else:
            query = query.filter(UserPreference.agent_id.is_(None))
        
        existing_prefs = query.first()
        
        if existing_prefs:
            # Update existing preferences
            logger.info(f"Updating existing preferences for user {preferences.user_id}")
            
            if preferences.communication_style is not None:
                existing_prefs.communication_style = preferences.communication_style
            if preferences.preferred_sources is not None:
                existing_prefs.preferred_sources = preferences.preferred_sources
            if preferences.notification_preferences is not None:
                existing_prefs.notification_preferences = preferences.notification_preferences
            
            db.commit()
            db.refresh(existing_prefs)
            
            return existing_prefs
        
        else:
            # Create new preferences
            logger.info(f"Creating new preferences for user {preferences.user_id}")
            
            new_prefs = UserPreference(
                user_id=preferences.user_id,
                company_id=company_id_uuid,
                agent_id=preferences.agent_id,
                communication_style=preferences.communication_style or 'detailed',
                preferred_sources=preferences.preferred_sources or [],
                notification_preferences=preferences.notification_preferences or {}
            )
            
            db.add(new_prefs)
            db.commit()
            db.refresh(new_prefs)
            
            return new_prefs
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating preferences: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preferences: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserPreferenceResponse)
async def get_preferences(
    user_id: str,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """
    Get user preferences.
    
    If agent_id is provided, returns agent-specific preferences if they exist,
    otherwise falls back to general user preferences.
    
    Requirements: 37.2, 37.6
    
    Args:
        user_id: User identifier
        agent_id: Optional agent identifier for agent-specific preferences
        db: Database session
        auth: Authentication context
        
    Returns:
        User preferences
        
    Raises:
        HTTPException: If preferences not found or company_id is missing
    """
    try:
        # Get company_id from auth context
        company_id = auth.company_id
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company_id is required in authentication context"
            )
        
        # Convert company_id string to UUID if needed
        if isinstance(company_id, str):
            company_id_uuid = uuid.UUID(company_id)
        else:
            company_id_uuid = company_id
        
        logger.info(
            f"Retrieving preferences for user {user_id}, "
            f"agent {agent_id}, company {company_id}"
        )
        
        # Query preferences
        query = db.query(UserPreference).filter(
            UserPreference.user_id == user_id,
            UserPreference.company_id == company_id_uuid
        )
        
        # If agent_id is provided, try to get agent-specific preferences first
        if agent_id:
            agent_prefs = query.filter(UserPreference.agent_id == agent_id).first()
            if agent_prefs:
                logger.info(f"Found agent-specific preferences for user {user_id}")
                return agent_prefs
        
        # Fall back to general user preferences (agent_id is NULL)
        general_prefs = query.filter(UserPreference.agent_id.is_(None)).first()
        if general_prefs:
            logger.info(f"Found general preferences for user {user_id}")
            return general_prefs
        
        # No preferences found
        logger.warning(f"No preferences found for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preferences not found for user {user_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preferences(
    user_id: str,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """
    Delete user preferences.
    
    If agent_id is provided, deletes only agent-specific preferences.
    Otherwise, deletes general user preferences.
    
    Requirements: 37.6
    
    Args:
        user_id: User identifier
        agent_id: Optional agent identifier for agent-specific preferences
        db: Database session
        auth: Authentication context
        
    Raises:
        HTTPException: If preferences not found or company_id is missing
    """
    try:
        # Get company_id from auth context
        company_id = auth.company_id
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company_id is required in authentication context"
            )
        
        # Convert company_id string to UUID if needed
        if isinstance(company_id, str):
            company_id_uuid = uuid.UUID(company_id)
        else:
            company_id_uuid = company_id
        
        logger.info(
            f"Deleting preferences for user {user_id}, "
            f"agent {agent_id}, company {company_id}"
        )
        
        # Query preferences
        query = db.query(UserPreference).filter(
            UserPreference.user_id == user_id,
            UserPreference.company_id == company_id_uuid
        )
        
        # Filter by agent_id
        if agent_id:
            query = query.filter(UserPreference.agent_id == agent_id)
        else:
            query = query.filter(UserPreference.agent_id.is_(None))
        
        prefs = query.first()
        
        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preferences not found for user {user_id}"
            )
        
        # Delete preferences
        db.delete(prefs)
        db.commit()
        
        logger.info(f"Deleted preferences for user {user_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preferences: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete preferences: {str(e)}"
        )


@router.get("", response_model=List[UserPreferenceResponse])
async def list_preferences(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """
    List all user preferences for the authenticated company.
    
    This endpoint is useful for administrators to view all user preferences
    in their organization.
    
    Requirements: 37.6
    
    Args:
        db: Database session
        auth: Authentication context
        
    Returns:
        List of all user preferences for the company
        
    Raises:
        HTTPException: If company_id is missing
    """
    try:
        # Get company_id from auth context
        company_id = auth.company_id
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company_id is required in authentication context"
            )
        
        # Convert company_id string to UUID if needed
        if isinstance(company_id, str):
            company_id_uuid = uuid.UUID(company_id)
        else:
            company_id_uuid = company_id
        
        logger.info(f"Listing all preferences for company {company_id}")
        
        # Query all preferences for the company
        preferences = db.query(UserPreference).filter(
            UserPreference.company_id == company_id_uuid
        ).all()
        
        logger.info(f"Found {len(preferences)} preference records for company {company_id}")
        
        return preferences
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list preferences: {str(e)}"
        )
