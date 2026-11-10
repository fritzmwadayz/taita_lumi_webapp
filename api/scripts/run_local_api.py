"""In-memory launcher for the TaitaLumi API — for local end-to-end testing
of test_api_endpoints.sh without a real Postgres.

It overrides get_db to use an in-memory store of users + edit_log entries,
so all the auth/profile/password-reset endpoints work end-to-end exactly as
they would against a real DB. Run with:

    DATABASE_URL=postgresql+asyncpg://x:x@localhost/x python -m scripts.run_local_api

Then point the test script at it:

    BASE_URL=http://localhost:8000 ./download/test_api_endpoints.sh

This launcher is a TEST HARNESS, not production code. It trades real
persistence for not needing Postgres installed locally.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import app.db as db_module
from app.models import EditLog, User


class InMemoryDB:
    """Tiny stand-in for AsyncSession, backed by Python dicts."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.edit_log: list[EditLog] = []

    async def execute(self, stmt: Any) -> "_Result":
        model_cls, filters, excluded_id = _inspect(stmt)

        if model_cls is User:
            if "id" in filters:
                return _Result(value=self.users.get(filters["id"]))
            if "email" in filters:
                target = (filters["email"] or "").lower()
                for u in self.users.values():
                    if (u.email or "").lower() == target:
                        if excluded_id is not None and u.id == excluded_id:
                            continue
                        return _Result(value=u)
                return _Result(value=None)
            return _Result(value=None)

        if model_cls is EditLog:
            return _Result(rows=list(self.edit_log))

        return _Result(value=None)

    async def scalar(self, stmt: Any) -> Any:
        return (await self.execute(stmt)).scalar_one_or_none()

    def add(self, obj: Any) -> None:
        if isinstance(obj, User):
            if getattr(obj, "id", None) is None or isinstance(obj.id, MagicMock):
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            self.users[obj.id] = obj
        elif isinstance(obj, EditLog):
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            self.edit_log.append(obj)

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: Any) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def delete(self, obj: Any) -> None:
        if isinstance(obj, User) and getattr(obj, "id", None) in self.users:
            self.users.pop(obj.id, None)


class _Result:
    def __init__(self, value: Any = None, rows: list[Any] | None = None) -> None:
        self._value = value
        self._rows = rows or []

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalar(self) -> Any:
        return self._value

    def scalars(self) -> "_Scalars":
        return _Scalars(self._rows)

    def all(self) -> list[Any]:
        return self._rows


class _Scalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows

    def unique(self) -> "_Scalars":
        return self


def _iter_whereclauses(stmt: Any):
    """Yield each WHERE clause from a SQLAlchemy Select.

    Handles both:
      - select(User).where(User.email == "x")        → whereclause is a single
        BinaryExpression (has .left/.right/.operator)
      - select(User).where(a).where(b) / where(a & b) → whereclause is a
        BooleanClauseList (iterate its .clauses or .get_children())
    """
    wc = stmt.whereclause
    if wc is None:
        return
    # Single BinaryExpression — yield it directly
    if hasattr(wc, "operator") and hasattr(wc, "left") and hasattr(wc, "right"):
        yield wc
        return
    # BooleanClauseList — iterate the sub-clauses
    clauses = getattr(wc, "clauses", None) or []
    for c in clauses:
        if hasattr(c, "operator") and hasattr(c, "left") and hasattr(c, "right"):
            yield c
        else:
            # Could be a nested clause list — recurse one level
            sub = getattr(c, "clauses", None) or []
            for sc in sub:
                yield sc


def _inspect(stmt: Any) -> tuple[type | None, dict[str, Any], uuid.UUID | None]:
    """Inspect a select() and return (model, {col: val filters}, excluded_id)."""
    # Detect model from the FROM clause (works for select(User) and
    # select(User.id, ...) — both put the entity in stmt.get_final_froms()).
    model_cls: type | None = None
    try:
        froms = stmt.get_final_froms()
        for f in froms:
            tbl_name = getattr(f, "name", None)
            for m in (User, EditLog):
                if m.__tablename__ == tbl_name:
                    model_cls = m
                    break
            if model_cls:
                break
    except Exception:
        pass

    # Extract equality + ne filters
    filters: dict[str, Any] = {}
    excluded_id: uuid.UUID | None = None
    for clause in _iter_whereclauses(stmt):
        op = getattr(clause, "operator", None)
        op_name = getattr(op, "__name__", "") if op is not None else ""

        left = getattr(clause, "left", None)
        right = getattr(clause, "right", None)
        if left is None or right is None:
            continue

        colname = getattr(left, "name", None) or getattr(left, "key", None)
        if not colname:
            continue

        val = getattr(right, "effective_value", None)
        if val is None:
            val = getattr(right, "value", None)

        if op_name == "eq":
            filters[colname] = val
        elif op_name == "ne" and colname == "id":
            if isinstance(val, uuid.UUID):
                excluded_id = val
            elif val:
                try:
                    excluded_id = uuid.UUID(str(val))
                except (ValueError, AttributeError, TypeError):
                    pass
    return model_cls, filters, excluded_id


# Avoid the lint of "unused import" if MagicMock import is removed
from unittest.mock import MagicMock  # noqa: E402


_in_memory_db = InMemoryDB()


async def fake_get_db():
    yield _in_memory_db


def main() -> None:
    import uvicorn

    from app.main import app

    app.dependency_overrides[db_module.get_db] = fake_get_db

    # Clear the in-memory rate-limit store on startup so re-runs work
    from app.anon import _password_reset_attempts
    _password_reset_attempts.clear()

    print("=" * 60)
    print("  TaitaLumi API — in-memory launcher (TEST HARNESS)")
    print("  No real DB; users stored in a Python dict.")
    print("  Hit http://localhost:8000/")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
