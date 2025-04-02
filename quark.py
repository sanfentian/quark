from typing import Tuple

import requests
import re
import time
import random
import logging

from services.disk_service import DiskService
from sqlite import PGDatabase
import sys
from pathlib import Path
logging.getLogger().setLevel(logging.INFO)
# 将项目根目录加入Python路径
sys.path.append(str(Path(__file__).parent))

from config.database import SessionLocal  # 导入您定义的SessionLocal

# 创建数据库会话
db = SessionLocal()



def get_id_from_url(url) -> str:
    """pwd_id"""
    pattern = r"/s/(\w+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ""


def generate_timestamp(length):
    timestamps = str(time.time() * 1000)
    return int(timestamps[0:length])


class Quark:
    ad_pwd_id = "0df525db2bd0"

    def __init__(self, cookie: str) -> None:
        self.headers = {
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'sec-ch-ua-mobile': '?0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'origin': 'https://pan.quark.cn',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://pan.quark.cn/',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': cookie}

    def store(self, file):
        pwd_id = get_id_from_url(file.original_url)
        #stoken = self.get_stoken(pwd_id)
        stoken, is_valid = quark.get_stoken_new(pwd_id)

        if not is_valid:
            # 获取原始URL（根据你的业务逻辑）
            original_url = f"https://pan.quark.cn/s/{pwd_id}"

            # 标记数据库记录
            DiskService.mark_invalid_resource(db, file.id)

            # 跳过当前处理
            return
        detail = self.detail(pwd_id, stoken)
        file_name = detail.get('title')
        if not DiskService.check_file_exists(db,file_name):
            first_id, share_fid_token, file_type = detail.get("fid"), detail.get("share_fid_token"), detail.get(
                "file_type")
            task = self.save_task_id(pwd_id, stoken, first_id, share_fid_token)
            data = self.task(task)
            file_id = data.get("data").get("save_as").get("save_as_top_fids")[0]
            if not file_type:
                dir_file_list = self.get_dir_file(file_id)
                self.del_ad_file(dir_file_list)
                # self.add_ad(file_id)
            share_task_id = self.share_task_id(file_id, file_name)
            share_id = self.task(share_task_id).get("data").get("share_id")
            share_link = self.get_share_link(share_id)
            DiskService.update_share_link(db, file.id,file_id, file_name, file_type, share_link)

    def get_stoken(self, pwd_id: str):
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc&uc_param_str=&__dt=405&__t={generate_timestamp(13)}"
        payload = {"pwd_id": pwd_id, "passcode": ""}
        headers = self.headers
        response = requests.post(url, json=payload, headers=headers).json()
        if response.get("data"):
            return response["data"]["stoken"]
        else:
            return ""

    def get_stoken_new(self, pwd_id: str) -> Tuple[str, bool]:
        """
        获取分享页的stoken，并返回是否有效

        参数:
            pwd_id: 分享链接ID

        返回:
            Tuple[stoken, is_valid]
            - stoken: 成功返回token，失败返回空字符串
            - is_valid: 分享链接是否有效
        """
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc&uc_param_str=&__dt=405&__t={generate_timestamp(13)}"
        payload = {"pwd_id": pwd_id, "passcode": ""}

        try:
            response = requests.post(url, json=payload, headers=self.headers).json()

            # 处理分享已取消的情况
            if response.get('code') == 41012:
                print(f"分享链接已失效: {pwd_id}")
                return "", False

            # 正常获取stoken
            if response.get("data"):
                return response["data"]["stoken"], True

            # 其他错误情况
            print(f"获取stoken失败: {response.get('message', '未知错误')}")
            return "", False

        except Exception as e:
            print(f"请求异常: {str(e)}")
            return "", False



    def detail(self, pwd_id, stoken):
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail"
        headers = self.headers
        params = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": 0,
            "_page": 1,
            "_size": "50",
        }

        response = requests.request("GET", url=url, headers=headers, params=params)
        id_list = response.json().get("data").get("list")[0]
        if id_list:
            data = {
                "title": id_list.get("file_name"),
                "file_type": id_list.get("file_type"),
                "fid": id_list.get("fid"),
                "pdir_fid": id_list.get("pdir_fid"),
                "share_fid_token": id_list.get("share_fid_token")
            }
            return data

    def save_task_id(self, pwd_id, stoken, first_id, share_fid_token, to_pdir_fid=0):
        logging.info("获取保存文件的TASKID")
        url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": generate_timestamp(13),
        }
        data = {"fid_list": [first_id],
                "fid_token_list": [share_fid_token],
                "to_pdir_fid": to_pdir_fid, "pwd_id": pwd_id,
                "stoken": stoken, "pdir_fid": "0", "scene": "link"}
        response = requests.request("POST", url, json=data, headers=self.headers, params=params)
        logging.info(response.json())
        task_id = response.json().get('data').get('task_id')
        return task_id

    def task(self, task_id, trice=10):
        """根据task_id进行任务"""
        logging.info("根据TASKID执行任务")
        trys = 0
        for i in range(trice):
            url = f"https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&uc_param_str=&task_id={task_id}&retry_index={range}&__dt=21192&__t={generate_timestamp(13)}"
            trys += 1
            response = requests.get(url, headers=self.headers).json()
            logging.info(response)
            if response.get('data').get('status'):
                return response
        return False

    def share_task_id(self, file_id, file_name):
        """创建分享任务ID"""
        url = "https://drive-pc.quark.cn/1/clouddrive/share?pr=ucpro&fr=pc&uc_param_str="
        data = {"fid_list": [file_id],
                "title": file_name,
                "url_type": 1, "expired_type": 1}
        response = requests.request("POST", url=url, json=data, headers=self.headers)
        return response.json().get("data").get("task_id")

    def get_share_link(self, share_id):
        url = "https://drive-pc.quark.cn/1/clouddrive/share/password?pr=ucpro&fr=pc&uc_param_str="
        data = {"share_id": share_id}
        response = requests.post(url=url, json=data, headers=self.headers)
        return response.json().get("data").get("share_url")

    def get_all_file(self):
        """获取所有文件id"""
        logging.info("正在获取所有文件")
        all_file = []
        url = "https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&uc_param_str=&pdir_fid=0&_page=1&_size=50&_fetch_total=1&_fetch_sub_dirs=0&_sort=file_type:asc,updated_at:desc"
        response = requests.get(url, headers=self.headers)
        files_list = response.json().get('data').get('list')
        for files in files_list:
            file_list = files.get("files")
            for i in file_list:
                all_file.append(i)
        return all_file

    def get_dir_file(self, dir_id) -> list:
        logging.info("正在遍历父文件夹")
        """获取指定文件夹的文件,后期可能会递归"""
        url = f"https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&uc_param_str=&pdir_fid={dir_id}&_page=1&_size=50&_fetch_total=1&_fetch_sub_dirs=0&_sort=updated_at:desc"
        response = requests.get(url=url, headers=self.headers)
        files_list = response.json().get('data').get('list')
        return files_list

    def del_file(self, file_id):
        logging.info("正在删除文件")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/delete?pr=ucpro&fr=pc&uc_param_str="
        data = {"action_type": 2, "filelist": [file_id], "exclude_fids": []}
        response = requests.post(url=url, json=data, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("data").get("task_id")
        return False

    def del_ad_file(self, file_list):
        logging.info("删除可能存在广告的文件")
        for file in file_list:
            file_name = file.get("file_name")
            from ad_check import ad_check
            if ad_check(file_name):
                task_id = self.del_file(file.get("fid"))
                self.task(task_id)

    def add_ad(self, dir_id):
        logging.info("添加个人自定义广告")
        pwd_id = self.ad_pwd_id
        stoken = self.get_stoken(pwd_id)
        detail = self.detail(pwd_id, stoken)
        first_id, share_fid_token = detail.get("fid"), detail.get("share_fid_token")
        task_id = self.save_task_id(pwd_id, stoken, first_id, share_fid_token, dir_id)
        self.task(task_id, 1)
        logging.info("广告移植成功")

    def search_file(self, file_name):
        logging.info("正在从网盘搜索文件🔍")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/search?pr=ucpro&fr=pc&uc_param_str=&_page=1&_size=50&_fetch_total=1&_sort=file_type:desc,updated_at:desc&_is_hl=1"
        params = {"q": file_name}
        response = requests.get(url=url, headers=self.headers, params=params)
        return response.json().get('data').get('list')


if __name__ == '__main__':
    cookie = '__wpkreporterwid_=fb058218-8d82-418f-bc4a-ce808a6ce446; ctoken=EjpfhpTwiyjP2cm_E8hcUxqU; web-grey-id=efa505b5-d991-4535-a566-ec18fe38e54a; web-grey-id.sig=fcdm6MG5aEHCu61cl711OI2aqMON8Dialy1DELnZgH4; b-user-id=2fd409f5-62a9-a3c9-287a-297a0540c9f7; b-user-id=2fd409f5-62a9-a3c9-287a-297a0540c9f7; grey-id=a5b4ad69-d102-105f-2ccc-bb0d258b8bb0; grey-id.sig=62ZnhTds0ocFsmSpqpAypYf1hPU7JQjuJVGuo9gVqOk; isQuark=true; isQuark.sig=hUgqObykqFom5Y09bll94T1sS9abT1X-4Df_lzgl8nM; __sdid=AAS/++jjqZnZ+rmfWrdt2PrAF7syYW0SIW/BX04hfsZQ8Da4LjVRwPEcfqLKyxTS1UI=; _UP_A4A_11_=wb9c714246ef47429fbf85f669f4b795; __wpkreporterwid_=fd3f82d0-6017-4818-b6b9-1db64ce2d166; xlly_s=1; __chkey=; _UP_D_=pc; _UP_30C_6A_=st9c762013al08smc0zveugeh5p9i6yx; _UP_TS_=sg19682378f90a6f44713895c320a533305; _UP_E37_B7_=sg19682378f90a6f44713895c320a533305; _UP_TG_=st9c762013al08smc0zveugeh5p9i6yx; _UP_335_2B_=1; __pus=5f00d9cc7f58550fad5b03506b491ce7AATYQLEFa2YUGRnSbNDcZmeZHS/B4AlyUB+O9dnHGbZU39ZRZXlWLY8yYDOJc4kqkQB9k3ENRzaj4ni1jGTTIUlf; __kp=34063b50-0d4a-11f0-9f04-3f7b8b6df25f; __kps=AAR8KDGzUx4Ufo5DQb68SNLG; __ktd=JyySgfo1DWb70kvozMYTkw==; __uid=AAR8KDGzUx4Ufo5DQb68SNLG; __puus=a6832e5ab0ab527588b712c51103dc18AAQ8agHzGDsyESRJ+KDUEemPeBaRTHQ5j31SN3JycT0XBwcbSkmCsv41Ns5gmh2YIHcKJ5lqQY+8QIq+t2/aZDxIGRfmF2etwdESGcKkiVtz5oP4eWXpUUniOUnGpDKBCiY5+/sgpqjNihDulZmwPC7eeIHA+Fot9Gq/PtcAC2TRSPNyvRXrHgAxvT3qHp56J+GU1ZAOTo9HZRzDfVgHlgLA; isg=BLm5VQQt-kGFZabrmTzT4VFEyCWTxq14wWE9WtvuNeBfYtn0Ixa9SCe05GaUQUWw; tfstk=ggainWaOGlo6cMeJBJu12dzqoxIK5Cgjd-LxHqHVYvkIH1NYgq84HS3t0ONYKxkE_nkqbiOEmfeYXn8VIJf0BSTxQAUxomy-7mZtHAHmoSwl9TQRy5NslDWReaFPOAmZlx7xuM3Ug1X8UTQRy5SZ1qFFePEKcRMogqlZbEJFtjHe3qkZ0p-Eavkqu-owYXlowxlq3f-FtjME3qu432lSCCkzuozFLI04al44oycijYPGVE80-UniU5kHuXansTMz_vY2uApp5aF36OY79VauEbeO8F2uNywnT87cKqwQ0-l0La9x5ue_PDVC4ePiSviz0DfN7W0iI0UqqIKsSoy_ocZMG_NE7JZSFcSCdX4TymDSxpWa9WDZqo2OdEkTqWyn2yppyqwQ0-l0Ldjz6H-yXZ8XxxKecniZOXDJCj8CsgouRA5ht3ZjbXGoe6fHcniZOXDRt6x51clIZYC..'
    quark = Quark(cookie)

    ###查库，拿出来需要保存的链接，
    # 获取第2页，每页20条
    try:
        # 调用服务方法
        unshared_files = DiskService.get_unshared_resources(db, page=1, page_size=200)
        # 在循环中添加错误重试机制
        max_retries = 3
        for file in unshared_files:
            for attempt in range(max_retries):
                try:
                    print(f"处理文件: {file.title} (尝试 {attempt + 1}/{max_retries})")

                    # 随机休眠 + 抖动（jitter）
                    base_sleep = 0  # 基础等待时间
                    jitter = random.uniform(-2, 2)  # 随机抖动
                    sleep_time = max(1, base_sleep + jitter)  # 确保不低于1秒

                    time.sleep(sleep_time)
                    quark.store(file)
                    break  # 成功则跳出重试循环

                except Exception as e:
                    print(f"处理失败: {str(e)}")
                    if attempt == max_retries - 1:
                        print("达到最大重试次数，跳过该文件")
                        break

    finally:
        # 确保关闭会话
        db.close()





