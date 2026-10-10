from alembic import op
import sqlalchemy as sa

revision = "0001_create_profiles"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("skills", sa.Text(), nullable=False, server_default=""),
        sa.Column("linkedin_url", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("department", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("availability", sa.String(length=20), nullable=False, server_default="OPEN_TO_TEAM"),
        sa.Column("visibility", sa.String(length=10), nullable=False, server_default="PUBLIC"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_profiles_availability", "profiles", ["availability"])

def downgrade():
    op.drop_index("ix_profiles_availability", table_name="profiles")
    op.drop_table("profiles")
