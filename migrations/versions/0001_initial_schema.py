"""建立校内测试环境所需的完整初始 Schema。"""

from alembic import op
from kylin_aiops_api.database import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """从空库创建当前全部业务表，保证首次部署具有确定结构。"""

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """仅用于一次性测试库回退；正式环境不得用它替代备份恢复。"""

    Base.metadata.drop_all(bind=op.get_bind())
