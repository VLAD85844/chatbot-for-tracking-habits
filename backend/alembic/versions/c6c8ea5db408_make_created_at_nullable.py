"""make_created_at_nullable

Revision ID: c6c8ea5db408
Revises: 476e1573437b
Create Date: 2025-04-26 21:45:36.798247

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# идентификаторы изменений
revision = 'c6c8ea5db408'
down_revision = '476e1573437b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('habits', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('habits', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    # ### end Alembic commands ###