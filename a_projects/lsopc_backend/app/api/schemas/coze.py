# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Optional, List, Any

class BaseCozeRequest(BaseModel):
    space_id: Optional[str] = None

class AddUrlRequest(BaseCozeRequest):
    dataset_id: str
    url: str
    name: str
    update_interval: Optional[int] = 24

class UrlItem(BaseModel):
    url: str
    name: str

class AddUrlBatchRequest(BaseCozeRequest):
    dataset_id: str
    urls: List[UrlItem]
    update_interval: Optional[int] = 24

class DatasetListRequest(BaseCozeRequest):
    page: int = 1
    page_size: int = 20
    name: Optional[str] = None

class FileListRequest(BaseCozeRequest):
    dataset_id: str
    page: int = 1
    size: int = 10

class CozeResponse(BaseModel):
    code: int
    msg: str
    data: Any
