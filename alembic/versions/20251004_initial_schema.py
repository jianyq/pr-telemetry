"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-10-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    # Note: Enum types are automatically created by SQLAlchemy when creating tables
    # No need to explicitly create them here
    
    # Create traces table
    op.create_table(
        'traces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('CREATED', 'INGESTING', 'COMPLETED', 'VALIDATING', 'VALIDATED', 'FAILED', name='tracestatus'), nullable=False),
        sa.Column('participant_id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('task_title', sa.String(), nullable=False),
        sa.Column('repo_origin', sa.String(), nullable=True),
        sa.Column('start_commit', sa.String(), nullable=True),
        sa.Column('upload_token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('num_events', sa.Integer(), nullable=True),
        sa.Column('last_seq', sa.Integer(), nullable=True),
        sa.Column('event_hash_chain', sa.String(), nullable=True),
        sa.Column('final_trace_uri', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_traces_id'), 'traces', ['id'], unique=False)
    op.create_index(op.f('ix_traces_participant_id'), 'traces', ['participant_id'], unique=False)
    op.create_index(op.f('ix_traces_task_id'), 'traces', ['task_id'], unique=False)
    op.create_index('ix_traces_upload_token', 'traces', ['upload_token'], unique=True)
    
    # Create trace_chunks table
    op.create_table(
        'trace_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('chunk_seq', sa.Integer(), nullable=False),
        sa.Column('storage_uri', sa.String(), nullable=False),
        sa.Column('num_events', sa.Integer(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['trace_id'], ['traces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trace_chunks_trace_id'), 'trace_chunks', ['trace_id'], unique=False)
    
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('artifact_type', sa.String(), nullable=False),
        sa.Column('storage_uri', sa.String(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['trace_id'], ['traces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artifacts_trace_id'), 'artifacts', ['trace_id'], unique=False)
    
    # Create qa_results table
    op.create_table(
        'qa_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('validation_tests_passed', sa.Boolean(), nullable=True),
        sa.Column('validation_framework', sa.String(), nullable=True),
        sa.Column('validation_num_passed', sa.Integer(), nullable=True),
        sa.Column('validation_num_failed', sa.Integer(), nullable=True),
        sa.Column('validation_runtime_s', sa.Float(), nullable=True),
        sa.Column('validation_container_image', sa.String(), nullable=True),
        sa.Column('validation_log_uri', sa.String(), nullable=True),
        sa.Column('judge_model', sa.String(), nullable=True),
        sa.Column('judge_model_version', sa.String(), nullable=True),
        sa.Column('judge_rubric_version', sa.String(), nullable=True),
        sa.Column('judge_feedback_summary', sa.Text(), nullable=True),
        sa.Column('score_problem_understanding', sa.Float(), nullable=True),
        sa.Column('score_causal_linking', sa.Float(), nullable=True),
        sa.Column('score_experiment_design', sa.Float(), nullable=True),
        sa.Column('score_efficiency', sa.Float(), nullable=True),
        sa.Column('score_reproducibility', sa.Float(), nullable=True),
        sa.Column('score_safety_hygiene', sa.Float(), nullable=True),
        sa.Column('score_overall', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['trace_id'], ['traces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_qa_results_trace_id'), 'qa_results', ['trace_id'], unique=True)
    
    # Create idempotency_keys table
    op.create_table(
        'idempotency_keys',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['trace_id'], ['traces.id'], ),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index(op.f('ix_idempotency_keys_key'), 'idempotency_keys', ['key'], unique=False)
    op.create_index(op.f('ix_idempotency_keys_trace_id'), 'idempotency_keys', ['trace_id'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f('ix_idempotency_keys_trace_id'), table_name='idempotency_keys')
    op.drop_index(op.f('ix_idempotency_keys_key'), table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
    op.drop_index(op.f('ix_qa_results_trace_id'), table_name='qa_results')
    op.drop_table('qa_results')
    op.drop_index(op.f('ix_artifacts_trace_id'), table_name='artifacts')
    op.drop_table('artifacts')
    op.drop_index(op.f('ix_trace_chunks_trace_id'), table_name='trace_chunks')
    op.drop_table('trace_chunks')
    op.drop_index('ix_traces_upload_token', table_name='traces')
    op.drop_index(op.f('ix_traces_task_id'), table_name='traces')
    op.drop_index(op.f('ix_traces_participant_id'), table_name='traces')
    op.drop_index(op.f('ix_traces_id'), table_name='traces')
    op.drop_table('traces')
    sa.Enum('CREATED', 'INGESTING', 'COMPLETED', 'VALIDATING', 'VALIDATED', 'FAILED', name='tracestatus').drop(op.get_bind())

