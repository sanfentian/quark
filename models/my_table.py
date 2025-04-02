from sqlalchemy import Column, Integer, String, Text, ARRAY, DateTime, Index, Boolean
from config.database import Base
from datetime import datetime

class CloudDiskResource(Base):
    __tablename__ = "cloud_disk_resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    original_url = Column(Text, unique=True)
    file_size = Column(Text)
    tags = Column(ARRAY(Text))
    channel = Column(String(100))
    group_chat = Column(String(100))
    disk_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    image_url = Column(Text)
    message_id = Column(String(30))
    saved_path = Column(Text)
    share_url = Column(Text)
    file_id = Column(String(255))
    file_name = Column(String(255))
    file_type = Column(Integer)
    share_link = Column(Text)
    # 默认值：default = True（新建记录默认标记为有效）
    # 约束：nullable = False（不允许为NULL）
    is_valid = Column(Boolean, default=True, nullable=False, comment='资源是否有效')
    # 失效原因（可选）
    invalid_reason = Column(String(255), nullable=True, comment='失效原因')

    # 查询优化索引（等同于SQL的CREATE INDEX）
    __table_args__ = (
        Index('idx_tags', tags, postgresql_using='gin'),
        Index('idx_disk_type', disk_type),
        Index('idx_created_at', created_at),
    )