"""Adding text type to google books URL

Revision ID: af93dc82f6cf
Revises: 14bbb6c1efde
Create Date: 2024-09-11 17:24:39.294997

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af93dc82f6cf'
down_revision = '14bbb6c1efde'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('_alembic_tmp_book')
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('google_books_url',
               existing_type=sa.VARCHAR(length=500),
               type_=sa.Text(),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('google_books_url',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=500),
               existing_nullable=True)

    op.create_table('_alembic_tmp_book',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('title', sa.VARCHAR(length=200), nullable=False),
    sa.Column('author', sa.VARCHAR(length=100), nullable=False),
    sa.Column('sentiment', sa.VARCHAR(length=20), nullable=False),
    sa.Column('position', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('google_books_url', sa.TEXT(), nullable=True),
    sa.Column('year_published', sa.INTEGER(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
