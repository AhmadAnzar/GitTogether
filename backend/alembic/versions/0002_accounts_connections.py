"""Accounts, connections and resumes.

- users: login accounts
- profiles.user_id: each profile belongs to one user (nullable: profiles created before accounts
  existed have no owner and become read-only)
- connections: PENDING requests and ACCEPTED (mutual) connections between users
- resumes: one PDF per profile, stored as bytes
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_accounts_connections"  # alembic_version.version_num is VARCHAR(32)
down_revision = "0001_create_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.add_column("profiles", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_profiles_user_id", "profiles", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_unique_constraint("uq_profiles_user_id", "profiles", ["user_id"])

    op.create_table(
        "connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addressee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_connections_pair"),
        sa.CheckConstraint("requester_id <> addressee_id", name="ck_connections_not_self"),
    )
    op.create_index("ix_connections_requester_id", "connections", ["requester_id"])
    op.create_index("ix_connections_addressee_id", "connections", ["addressee_id"])

    op.create_table(
        "resumes",
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("filename", sa.String(length=200), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("resumes")
    op.drop_index("ix_connections_addressee_id", table_name="connections")
    op.drop_index("ix_connections_requester_id", table_name="connections")
    op.drop_table("connections")
    op.drop_constraint("uq_profiles_user_id", "profiles", type_="unique")
    op.drop_constraint("fk_profiles_user_id", "profiles", type_="foreignkey")
    op.drop_column("profiles", "user_id")
    op.drop_table("users")
