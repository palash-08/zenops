"""Add server_inventories table

Revision ID: 1234567890ab
Revises: 
Create Date: 2026-07-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('server_inventories',
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hostname', sa.String(), nullable=True),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('services', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('server_id')
    )

def downgrade() -> None:
    op.drop_table('server_inventories')
