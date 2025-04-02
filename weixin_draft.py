from config.database import SessionLocal  # 导入您定义的SessionLocal

# 创建数据库会话
db = SessionLocal()
import random

from services.disk_service import DiskService
from config.database import SessionLocal  # 导入您定义的SessionLocal
from wechat_article_text.article_generator import  generate_resources_content
import json

from wechat_article_text.wechat_api import WeChatAPI

# 创建数据库会话

if __name__ == '__main__':

    db = SessionLocal()


    # 初始化 WeChatAPI
    # 1. 读取配置
    # 正确写法：强制使用 UTF-8 编码
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 初始化 WeChatAPI
    account = config["wechat_accounts"]["一颗半牛油果"]

    app_id = account["app_id"]
    app_secret = account["app_secret"]
    wechat_api = WeChatAPI(app_id, app_secret)
    # 搜索资源
    resources = DiskService.search_valid_resources(
        db,
        page=1
    )


    urls = []
    try:
        material_list = []

        random_number = random.randint(1, 870)
        count = 100

        while count > 0:
            # 每次获取 20 条数据
            material_list = wechat_api.get_permanent_material_list("image", offset=random_number, count=20)
            if material_list:  # 确保返回值不为空
                urls.extend([item['url'] for item in material_list['item']])
            random_number +=20
            count -= 20  # 更新 count

        print("素材列表:")
        print(json.dumps(material_list, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"获取素材列表失败: {e}")

    for res in resources:
        print(res)

    content_html = generate_resources_content(resources,wechat_api)

    print(content_html)

    # thumb_media_id = upload_thumb_media(access_token,local_image_path,"thumb")
    # print("thumb_media_id：", thumb_media_id)
    # if not thumb_media_id:
    #     exit()

    # # 5. 选取文章封面
    thumb_media_id = material_list['item'][0]['media_id']

    summary_lines = [
        f"{i + 1}. {resource.get('title', '')}"
        for i, resource in enumerate(resources)
    ]
    summary = "\n".join(summary_lines)
    print(f"摘要：\n{summary}")

    # 6. 创建草稿
    media_id = wechat_api.create_draft("每天十个强大的资源", ''.join(summary)[:110], content_html, thumb_media_id)

    print("media_id：", media_id)
    if not media_id:
        exit()