from uuid import uuid4

from app.models import ChatMessage, ChatThread


class TestChatThreadModel:
    """Test ChatThread model structure and constraints."""

    def test_chat_thread_table_exists(self):
        """Verify chatthread table structure."""
        table = ChatThread.__table__
        columns = {col.name for col in table.columns}

        assert "id" in columns
        assert "user_a_id" in columns
        assert "user_b_id" in columns
        assert "last_message_at" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_chat_thread_nullability(self):
        """Verify nullable columns."""
        table = ChatThread.__table__
        columns = {col.name: col for col in table.columns}

        assert not columns["id"].nullable
        assert not columns["user_a_id"].nullable
        assert not columns["user_b_id"].nullable
        assert columns["last_message_at"].nullable
        assert not columns["created_at"].nullable
        assert not columns["updated_at"].nullable

    def test_chat_thread_unique_constraint(self):
        """Verify unique constraint on (user_a_id, user_b_id)."""
        table = ChatThread.__table__
        constraints = {
            constraint.name: constraint
            for constraint in table.constraints
            if hasattr(constraint, "name") and constraint.name
        }

        assert "uq_chat_thread_users" in constraints

    def test_chat_thread_check_constraint(self):
        """Verify check constraint on user_a_id < user_b_id."""
        table = ChatThread.__table__
        constraints = {
            constraint.name: constraint
            for constraint in table.constraints
            if hasattr(constraint, "name") and constraint.name
        }

        assert "ck_chat_thread_user_order" in constraints

    def test_chat_thread_foreign_keys(self):
        """Verify foreign key relationships."""
        table = ChatThread.__table__
        fk_columns = {fk.parent.name for fk in table.foreign_keys}

        assert "user_a_id" in fk_columns
        assert "user_b_id" in fk_columns

    def test_chat_thread_indexes(self):
        """Verify created_at and user_id indexes."""
        table = ChatThread.__table__
        index_columns = {}
        for idx in table.indexes:
            for col in idx.expressions:
                col_name = str(col).split(".")[-1]
                index_columns[col_name] = True

        assert "created_at" in index_columns
        assert "user_a_id" in index_columns
        assert "user_b_id" in index_columns


class TestChatMessageModel:
    """Test ChatMessage model structure and constraints."""

    def test_chat_message_table_exists(self):
        """Verify chatmessage table structure."""
        table = ChatMessage.__table__
        columns = {col.name for col in table.columns}

        assert "id" in columns
        assert "thread_id" in columns
        assert "sender_id" in columns
        assert "body" in columns
        assert "attachment_book_id" in columns
        assert "attachment_collection_id" in columns
        assert "read_at" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_chat_message_nullability(self):
        """Verify nullable columns."""
        table = ChatMessage.__table__
        columns = {col.name: col for col in table.columns}

        assert not columns["id"].nullable
        assert not columns["thread_id"].nullable
        assert not columns["sender_id"].nullable
        assert not columns["body"].nullable
        assert columns["attachment_book_id"].nullable
        assert columns["attachment_collection_id"].nullable
        assert columns["read_at"].nullable
        assert not columns["created_at"].nullable
        assert not columns["updated_at"].nullable

    def test_chat_message_foreign_keys(self):
        """Verify foreign key relationships."""
        table = ChatMessage.__table__
        fk_columns = {fk.parent.name for fk in table.foreign_keys}

        assert "thread_id" in fk_columns
        assert "sender_id" in fk_columns
        assert "attachment_book_id" in fk_columns
        assert "attachment_collection_id" in fk_columns

    def test_chat_message_indexes(self):
        """Verify thread_id, sender_id, and attachment indexes."""
        table = ChatMessage.__table__
        index_columns = {}
        for idx in table.indexes:
            for col in idx.expressions:
                col_name = str(col).split(".")[-1]
                index_columns[col_name] = True

        assert "thread_id" in index_columns
        assert "sender_id" in index_columns
        assert "attachment_book_id" in index_columns
        assert "attachment_collection_id" in index_columns
        assert "created_at" in index_columns

    def test_chat_message_default_nullable_fields(self):
        """Verify default values for nullable fields."""
        msg = ChatMessage(
            thread_id=uuid4(),
            sender_id=uuid4(),
            body="test message",
        )

        assert msg.attachment_book_id is None
        assert msg.attachment_collection_id is None
        assert msg.read_at is None
