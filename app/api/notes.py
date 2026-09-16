import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import note as note_crud
from app.models.user import User
from app.schemas.note import NoteCreate, NotePage, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_in: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await note_crud.create_note(db, note_in, owner_id=current_user.id)


@router.get("", response_model=NotePage)
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    tag: str | None = Query(None, description="Filter notes by a single tag"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes, total = await note_crud.list_notes(
        db, owner_id=current_user.id, page=page, page_size=page_size, tag=tag
    )
    pages = math.ceil(total / page_size) if total else 0
    return NotePage(items=notes, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await note_crud.get_note(db, note_id, owner_id=current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: uuid.UUID,
    note_in: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await note_crud.get_note(db, note_id, owner_id=current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return await note_crud.update_note(db, note, note_in)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await note_crud.get_note(db, note_id, owner_id=current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await note_crud.delete_note(db, note)
