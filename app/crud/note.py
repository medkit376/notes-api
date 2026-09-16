import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate


async def create_note(db: AsyncSession, note_in: NoteCreate, owner_id: uuid.UUID) -> Note:
    note = Note(**note_in.model_dump(), owner_id=owner_id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def get_note(db: AsyncSession, note_id: uuid.UUID, owner_id: uuid.UUID) -> Note | None:
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def list_notes(
    db: AsyncSession,
    owner_id: uuid.UUID,
    page: int = 1,
    page_size: int = 10,
    tag: str | None = None,
) -> tuple[list[Note], int]:
    base_query = select(Note).where(Note.owner_id == owner_id)
    count_query = select(func.count()).select_from(Note).where(Note.owner_id == owner_id)

    if tag:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            base_query = base_query.where(func.array_position(Note.tags, tag).isnot(None))
            count_query = count_query.where(func.array_position(Note.tags, tag).isnot(None))
        else:
            # Non-Postgres dialects (e.g. SQLite in tests) store tags as
            # JSON, so containment is checked in Python after fetching.
            all_result = await db.execute(base_query)
            filtered_ids = [n.id for n in all_result.scalars().all() if tag in n.tags]
            base_query = base_query.where(Note.id.in_(filtered_ids))
            count_query = count_query.where(Note.id.in_(filtered_ids))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    base_query = (
        base_query.order_by(Note.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(base_query)
    notes = list(result.scalars().all())
    return notes, total


async def update_note(db: AsyncSession, note: Note, note_in: NoteUpdate) -> Note:
    update_data = note_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note: Note) -> None:
    await db.delete(note)
    await db.commit()
