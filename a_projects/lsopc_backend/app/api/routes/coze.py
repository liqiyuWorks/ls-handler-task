# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, UploadFile, File, Header, HTTPException, Body
from typing import Optional, List
from app.services.coze_service import CozeService
from app.api.schemas.coze import AddUrlRequest, AddUrlBatchRequest

router = APIRouter()

def get_coze_service(
    x_coze_token: Optional[str] = Header(None, alias="x-coze-token"),
    x_coze_space_id: Optional[str] = Header(None, alias="x-coze-space-id")
) -> CozeService:
    if not x_coze_token:
        raise HTTPException(status_code=401, detail="Missing x-coze-token header")
    return CozeService(token=x_coze_token, space_id=x_coze_space_id)

@router.get("/datasets")
async def list_datasets(
    page: int = 1,
    page_size: int = 20,
    name: Optional[str] = None,
    service: CozeService = Depends(get_coze_service)
):
    try:
        return service.list_datasets(page=page, page_size=page_size, name=name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/datasets/{dataset_id}/files")
async def list_files(
    dataset_id: str,
    page: int = 1,
    size: int = 10,
    service: CozeService = Depends(get_coze_service)
):
    try:
        return service.list_files(dataset_id=dataset_id, page=page, size=size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/upload")
async def upload_files(
    dataset_id: str = Body(...),
    files: List[UploadFile] = File(...),
    service: CozeService = Depends(get_coze_service)
):
    """
    Batch upload files (up to 10 recommended).
    Iterates and uploads one by one.
    """
    results = []
    # Limit reasonable batch size on backend if needed, but frontend also limits.
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 files per batch")

    for file in files:
        try:
            content = await file.read()
            res = service.upload_file(
                dataset_id=dataset_id,
                file_content=content,
                file_name=file.filename
            )
            results.append({"filename": file.filename, "status": "success", "data": res})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "error": str(e)})
            
    return {"results": results}

@router.post("/urls/add")
async def add_urls(
    request: AddUrlBatchRequest,
    service: CozeService = Depends(get_coze_service)
):
    """Batch add URLs"""
    try:
        sid = request.space_id if request.space_id else service.space_id
        # Convert Pydantic models to dicts
        urls_dict = [{"url": u.url, "name": u.name} for u in request.urls]
        
        return service.add_urls_batch(
            dataset_id=request.dataset_id,
            urls=urls_dict,
            space_id=sid,
            update_interval=request.update_interval or 24
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
