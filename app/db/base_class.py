import re
from typing import Any

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base class.
    Automatically generates table names from camel-cased class definitions.
    """
    id: Any  # Keep it generic here; specific classes define exact Mapped structures

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # E.g., UserProfile -> user_profiles
        name = cls.__name__
        # Insert underscore before uppercase letters (except at start) and lowercase it
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        # Simple pluralization suffix
        if snake.endswith("y"):
            return f"{snake[:-1]}ies"
        elif snake.endswith("s"):
            return f"{snake}es"
        return f"{snake}s"
