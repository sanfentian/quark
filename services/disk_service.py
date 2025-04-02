from datetime import datetime

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from pathlib import Path
# 配置路径
from pathlib import Path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
from models.my_table import CloudDiskResource


class DiskService:
    # SQLAlchemy方式
    @staticmethod
    def create_resource(db: Session, resource_data: dict):
        db_resource = CloudDiskResource(**resource_data)
        db.add(db_resource)
        db.commit()
        db.refresh(db_resource)
        return db_resource


    @staticmethod
    def get_unshared_resources(
            db: Session,
            page: int = 1,
            page_size: int = 10
    ) -> List[CloudDiskResource]:
        """
        获取未分享的资源（按创建时间倒序分页）

        参数:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量

        返回:
            资源对象列表
        """
        return db.query(CloudDiskResource) \
            .filter(CloudDiskResource.share_link == None) \
            .order_by(desc(CloudDiskResource.created_at)) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()  # ✅ 关键：执行查询


    @staticmethod
    def update_share_link(
            db: Session,
            resource_id: int,
            new_file_id,
            new_file_name,
            new_file_type,
            new_share_link: str
    ) -> Optional[CloudDiskResource]:
        """
        更新资源分享链接

        参数:
            db: 数据库会话
            resource_id: 资源ID
            new_share_link: 新的分享链接

        返回:
            更新后的资源对象（如果存在）
        """
        resource = db.query(CloudDiskResource) \
            .filter(CloudDiskResource.id == resource_id) \
            .first()

        if resource:
            resource.file_id = new_file_id
            resource.file_name = new_file_name
            resource.file_type = new_file_type
            resource.share_link = new_share_link
            db.commit()
            db.refresh(resource)
            return resource
        return None

    @staticmethod
    def check_file_exists(db: Session, file_name: str) -> bool:
        """
        检查文件名是否已存在（新表版本）

        参数:
            db: 数据库会话
            file_name: 要检查的文件名

        返回:
            bool: 存在返回True，不存在返回False
        """
        return db.query(
            db.query(CloudDiskResource)
            .filter(CloudDiskResource.file_name == file_name)
            .exists()
        ).scalar()

    @staticmethod
    def insert_resource(
            db: Session,
            file_id: str,
            file_name: str,
            file_type: int,
            share_link: str,
            **kwargs
    ) -> CloudDiskResource:
        """
        插入新资源记录（新表版本）

        参数:
            db: 数据库会话
            file_id: 文件唯一ID
            file_name: 文件名
            file_type: 文件类型
            share_link: 分享链接
            kwargs: 其他可选字段（如title, description等）

        返回:
            新创建的资源对象
        """
        resource_data = {
            'file_id': file_id,
            'file_name': file_name,
            'file_type': file_type,
            'share_link': share_link,
            **kwargs
        }
        return DiskService.create_resource(db, resource_data)

    @staticmethod
    def update_resource(
            db: Session,
            file_id: str,
            file_name: str,
            **kwargs
    ) -> Optional[CloudDiskResource]:
        """
        更新资源信息（新表版本）

        参数:
            db: 数据库会话
            file_id: 要更新的文件ID
            file_name: 新的文件名
            kwargs: 其他可更新字段

        返回:
            更新后的资源对象（如果存在）
        """
        resource = db.query(CloudDiskResource) \
            .filter(CloudDiskResource.file_id == file_id) \
            .first()

        if resource:
            resource.file_name = file_name
            for key, value in kwargs.items():
                setattr(resource, key, value)
            db.commit()
            db.refresh(resource)
            return resource
        return None

    @staticmethod
    def mark_invalid_resource(db: Session, new_id: int):
        """
        标记资源为无效

        参数:
            db: 数据库会话
            original_url: 原始分享链接
        """
        resource = db.query(CloudDiskResource) \
            .filter(CloudDiskResource.id == new_id) \
            .first()

        if resource:
            # 添加失效标记字段（假设表中有is_valid字段）
            resource.is_valid = False
            resource.updated_at = datetime.now()
            db.commit()
            print(f"已标记资源无效: {new_id}")

    @staticmethod
    def search_valid_resources(
            db: Session,
            keyword: str = None,
            tags: List[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> List[dict]:
        """
        带条件搜索有效资源

        参数:
            db: 数据库会话
            keyword: 标题/描述关键词
            tags: 标签列表
            page: 页码
            page_size: 每页数量
        """
        query = db.query(CloudDiskResource) \
            .filter(CloudDiskResource.is_valid == True)

        if keyword:
            query = query.filter(
                or_(
                    CloudDiskResource.title.contains(keyword),
                    CloudDiskResource.description.contains(keyword)
                )
            )

        if tags:
            query = query.filter(CloudDiskResource.tags.contains(tags))

        resources = query \
            .order_by(desc(CloudDiskResource.created_at)) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return DiskService._format_resources(resources)

    @staticmethod
    def _format_resources(resources: List[CloudDiskResource]) -> List[dict]:
        """内部格式化方法（处理特殊文件大小）"""
        formatted = []
        for r in resources:
            # 处理文件大小（N开头、A开头或空值都显示为未知）
            file_size = r.file_size or ''
            if file_size.lower().startswith(('n', 'a')):
                display_size = "大小未知"
            else:
                display_size = f"📁 {file_size}" if file_size else "大小未知"

            formatted.append({
                "title": r.title,
                "description": r.description or "暂无描述",
                "share_link": r.share_link or "链接未生成",
                "file_size": display_size,
                "tags": f" {' '.join(f'#{tag}' for tag in r.tags) if r.tags else '#无标签'}",
                "image_url": r.image_url or "无封面图",
            })
        return formatted