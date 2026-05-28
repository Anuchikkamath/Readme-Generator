"""
Project API Routes
Handles project-related endpoints for sync and README generation.
"""

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx

from app.services.pipeline import sync
from app.services.storage.postgres_client import PostgresClient
from app.services.llm.readme_generator import ReadmeGenerator
from app.services.llm.diagram_generator import DiagramGenerator
from app.services.llm.folder_structure_generator import FolderStructureGenerator
from app.core.security import get_current_user
from app.services.auth.token_manager import TokenManager
from app.core.config import settings

router = APIRouter(
    prefix="",
    tags=["projects"],
    responses={404: {"description": "Not found"}}
)

# Initialize clients
postgres_client = PostgresClient()
token_manager = TokenManager()


class GenerateReadmeRequest(BaseModel):
    """Request model for README generation."""
    project_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    meeting_ids: Optional[list[str]] = None


class GenerateDiagramRequest(BaseModel):
    """Request model for Mermaid diagram generation."""
    readme_content: str
    diagram_kind: Optional[str] = "flowchart"


class RenderDiagramRequest(BaseModel):
    """Request model for diagram rendering/export."""
    mermaid_code: str
    format: Optional[str] = "svg"

class CreateFolderStructureRequest(BaseModel):
    """Request model for folder structure generation from architecture diagram."""
    mermaid_code: str
    diagram_kind: Optional[str] = "flowchart"
    project_name: Optional[str] = None


def _validate_mermaid_text(mermaid_code: str) -> str:
    """Apply basic server-side validation before rendering/export."""
    code = (mermaid_code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Mermaid code is empty")

    if len(code) > 10000:
        raise HTTPException(status_code=400, detail="Mermaid code exceeds 10000 characters")

    blocked_tokens = ["<script", "javascript:", "onerror=", "onclick="]
    lower = code.lower()
    for token in blocked_tokens:
        if token in lower:
            raise HTTPException(status_code=400, detail="Unsafe Mermaid content detected")

    return code


@router.post("/sync", summary="Sync emails and process meeting notes")
async def sync_endpoint(current_user: dict = Depends(get_current_user)):
    """
    Sync endpoint - runs the pipeline to process emails and store meeting notes.
    
    **Protected Route**: Requires JWT authentication.
    
    This endpoint:
    - Fetches emails from the authenticated user's Gmail
    - Extracts Google Docs links from emails
    - Processes documents and extracts structured data using LLM
    - Stores meeting notes in the database with user_id for isolation
    
    Args:
        current_user: Current authenticated user (injected by dependency)
    
    Returns:
        dict: Status and summary of the sync operation including:
            - status: "sync completed" or "sync failed"
            - emails_fetched: Number of emails processed
            - meetings_stored: Number of meetings stored
            - processed: Number successfully processed
            - skipped: Number skipped/failed
    """
    try:
        print(f"[DEBUG] Sync endpoint called by user {current_user.get('user_id')}")
        
        # Get full user data from database
        user = postgres_client.get_user_by_id(current_user['user_id'])
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check and refresh token if needed
        valid_token = await token_manager.get_valid_token(user)
        
        if not valid_token:
            print(f"[ERROR] Failed to get valid token for user {user['email']}")
            raise HTTPException(
                status_code=401,
                detail="Failed to get valid access token. Please re-authenticate."
            )
        
        # Update user dict with fresh token
        user['access_token'] = valid_token
        
        print(f"[DEBUG] Starting sync for user {user['email']}")
        # Run sync with user's access token
        result = sync(current_user=user, user_id=user['id'])
        print(f"[DEBUG] Sync completed for user {user['email']}: {result.get('status')}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/projects", summary="Get all available projects")
async def get_projects(current_user: dict = Depends(get_current_user)):
    """
    Get all available projects for the authenticated user.
    
    **Protected Route**: Requires JWT authentication.
    
    Args:
        current_user: Current authenticated user (injected by dependency)
    
    Returns:
        dict: List of user's projects with canonical and normalized names
    """
    try:
        # Filter projects by user_id
        current_user_id = current_user.get('id') or current_user.get('user_id')
        projects = postgres_client.get_projects_for_user(current_user_id)
        
        project_list = []
        if projects:
            for canonical, normalized in projects:
                project_list.append({
                    "canonical_name": canonical,
                    "normalized_name": normalized
                })
        
        return {"projects": project_list}
    except Exception as e:
        # Return empty list on error to maintain API contract
        return {"projects": []}


@router.get("/projects/{project_id}", summary="Get project details and meetings")
async def get_project_details(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get project details and all associated meeting notes.
    
    Args:
        project_id: Project identifier (normalized or canonical name)
        current_user: Authenticated user
        
    Returns:
        dict: Project metadata and list of meetings
    """
    try:
        # Resolve project name (need to search ALL projects to find the name mapping)
        # Note: We still resolve against global metadata to find the TABLE name
        project_lower = project_id.lower().strip()
        all_projects = postgres_client.get_all_projects()
        
        canonical_name = None
        table_name = None
        
        # 1. Try exact match on normalized name
        for canonical, normalized in all_projects:
            if normalized == project_lower:
                canonical_name = canonical
                table_name = normalized
                break
        
        # 2. Try match on canonical name
        if not table_name:
            for canonical, normalized in all_projects:
                if canonical.lower() == project_lower:
                    canonical_name = canonical
                    table_name = normalized
                    break
        
        if not table_name:
            # If no global mapping, maybe it doesn't exist at all
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Fetch data FILTERED BY USER
        current_user_id = current_user.get('id') or current_user.get('user_id')
        columns, rows = postgres_client.fetch_project_data(table_name, user_id=current_user_id)
        
        # If no rows found for THIS user, effectively project is not found/empty for them
        # (unless we want to show empty project shell? User said "show projects fetched from that mail id")
        # If rows empty, it means they have no data.
        
        # Transform rows to frontend-friendly format
        meetings = []
        for row in rows:
            # Create a safe copy to avoid modifying original
            meeting = row.copy()
            
            # Map standard fields
            mapped_meeting = {
                "id": str(meeting.get('id', '')),
                "title": meeting.get('meeting_context', 'Meeting Note'),
                "date": meeting.get('meeting_date') or meeting.get('created_at'),
                "duration": meeting.get('duration', 30), # Default fallback
                "participants": [], # Not currently stored parsed
                "transcript": [] # Need to parse transcript if stored
            }
            
            # If there's a body or content field, use it as transcript/summary
            # For now, we return raw data and lets frontend handle display
            mapped_meeting.update(meeting)
            
            meetings.append(mapped_meeting)
            
        return {
            "id": table_name,
            "name": canonical_name,
            "meetings": meetings,
            "meeting_count": len(meetings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project details: {str(e)}")


@router.post("/generate-readme", summary="Generate README for a project")
async def generate_readme(request: GenerateReadmeRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate README for a project by aggregating meeting data.
    
    **Protected Route**: Requires JWT authentication.
    
    This endpoint:
    - Resolves the project ID to canonical and table names
    - Fetches meeting data from the database (filtered by user_id)
    - Optionally filters by date range (start_date, end_date)
    - Generates a professional README using LLM
    - Saves README to disk and stores in database
    
    Args:
        request: GenerateReadmeRequest with:
            - project_id: Project identifier (canonical or normalized name)
            - start_date: Optional start date filter (YYYY-MM-DD)
            - end_date: Optional end date filter (YYYY-MM-DD)
        current_user: Current authenticated user (injected by dependency)
        
    Returns:
        dict: Status of README generation including:
            - status: "README generated"
            - project: Canonical project name
            - filepath: Path to saved README file
            - meetings_processed: Number of meetings used
    """
    try:
        
        # Resolve project name (similar to scripts/generate_project_readme.py)
        project_lower = request.project_id.lower().strip()
        projects = postgres_client.get_all_projects()
        
        canonical_name = None
        table_name = None
        
        # Find matching project
        for canonical, normalized in projects:
            if normalized == project_lower or canonical.lower() == project_lower:
                canonical_name = canonical
                table_name = normalized
                break
        
        # Check if table exists directly
        if not table_name and postgres_client.project_table_exists(project_lower):
            canonical_name = request.project_id
            table_name = project_lower
        
        # Partial match fallback
        if not table_name:
            for canonical, normalized in projects:
                if project_lower in normalized or project_lower in canonical.lower():
                    canonical_name = canonical
                    table_name = normalized
                    break
        
        if not table_name:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{request.project_id}' not found"
            )
        
        # Fetch project data
        columns, rows = postgres_client.fetch_project_data(table_name)
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for project '{request.project_id}'"
            )
        
        # Apply date filters if provided
        if request.start_date or request.end_date:
            filtered_rows = []
            for row in rows:
                meeting_date = row.get('meeting_date')
                if not meeting_date:
                    continue
                
                if request.start_date and meeting_date < request.start_date:
                    continue
                if request.end_date and meeting_date > request.end_date:
                    continue
                
                filtered_rows.append(row)
            rows = filtered_rows
            
        # Apply meeting ID filter if provided (User Selection) and has priority over dates if both present
        if request.meeting_ids:
            # Filter rows where ID matches one in the list
            # Ensure ID comparison is robust (string vs int)
            target_ids = set(str(mid) for mid in request.meeting_ids)
            rows = [r for r in rows if str(r.get('id', '')) in target_ids]
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for project '{request.project_id}' in the specified date range"
            )
        
        # Generate README
        generator = ReadmeGenerator()
        readme_content = generator.generate(
            project_name=canonical_name,
            rows=rows,
            columns=columns
        )
        
        # Save to disk
        filepath = generator.save_to_disk(
            project_name=canonical_name,
            content=readme_content,
            output_dir="readmes"
        )
        
        # Store in database
        readme_id = None
        try:
            readme_id = postgres_client.store_readme(
                project_name=canonical_name,
                normalized_name=table_name,
                content=readme_content,
                model="gpt-4o-mini",
                meeting_count=len(rows)
            )
        except Exception as e:
            # Non-fatal error
            print(f"Warning: Failed to store README in DB: {e}")
        
        return {
            "status": "README generated",
            "project": canonical_name,
            "readme_content": readme_content,
            "meetings_processed": len(rows),
            "readme_id": readme_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"README generation failed: {str(e)}")


@router.post("/generate-diagram", summary="Generate Mermaid diagram from README content")
async def generate_diagram(request: GenerateDiagramRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate Mermaid source code from README markdown.

    **Protected Route**: Requires JWT authentication.
    """
    try:
        content = (request.readme_content or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="README content is required")

        generator = DiagramGenerator()
        mermaid_code = generator.generate(
            readme_content=content,
            diagram_kind=request.diagram_kind or "flowchart"
        )
        mermaid_code = _validate_mermaid_text(mermaid_code)

        first_line = mermaid_code.splitlines()[0].strip() if mermaid_code.splitlines() else ""
        return {
            "status": "diagram generated",
            "diagram_kind": request.diagram_kind or "flowchart",
            "detected_type_hint": first_line,
            "mermaid_code": mermaid_code,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagram generation failed: {str(e)}")


@router.post("/render-diagram", summary="Render Mermaid to SVG/PNG/PDF via Kroki")
async def render_diagram(request: RenderDiagramRequest, current_user: dict = Depends(get_current_user)):
    """
    Render Mermaid source into an output artifact through Kroki.

    **Protected Route**: Requires JWT authentication.
    """
    content_types = {
        "svg": "image/svg+xml",
        "png": "image/png",
        "pdf": "application/pdf",
    }

    output_format = (request.format or "svg").strip().lower()
    if output_format not in content_types:
        raise HTTPException(status_code=400, detail="Invalid format. Use svg, png, or pdf")

    mermaid_code = _validate_mermaid_text(request.mermaid_code)
    kroki_base = settings.KROKI_BASE_URL.rstrip("/")
    kroki_url = f"{kroki_base}/mermaid/{output_format}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            kroki_response = await client.post(
                kroki_url,
                content=mermaid_code.encode("utf-8"),
                headers={"Content-Type": "text/plain; charset=utf-8"}
            )

        if kroki_response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Diagram render provider failed ({kroki_response.status_code})"
            )

        return Response(
            content=kroki_response.content,
            media_type=content_types[output_format],
            headers={
                "Content-Disposition": f'attachment; filename="diagram.{output_format}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagram rendering failed: {str(e)}")


@router.post("/create-folder-structure", summary="Create folder structure and requirements.txt from architecture diagram")
async def create_folder_structure(request: CreateFolderStructureRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate project folder structure and a basic requirements.txt from Mermaid architecture input.

    **Protected Route**: Requires JWT authentication.
    """
    try:
        mermaid_code = _validate_mermaid_text(request.mermaid_code)
        generator = FolderStructureGenerator()
        result = generator.generate(
            mermaid_code=mermaid_code,
            diagram_kind=request.diagram_kind,
            project_name=request.project_name
        )
        return {
            "status": "folder structure generated",
            "diagram_kind": request.diagram_kind or "flowchart",
            "project_name": request.project_name or "GeneratedProject",
            "folder_structure": result["folder_structure"],
            "requirements_txt": result["requirements_txt"],
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Folder structure generation failed: {str(e)}")
