import logging
import random
import requests
import time
import datetime
import utils.util as util

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'


def success(response_json) -> bool:
    """
    检测接口返回是否存在错误
    :param response_json: 网络返回内容的json信息
    :return: 正确时返回true，错误时返回false
    :raises: 接口错误时直接抛出异常
    """
    status = response_json.get('status')
    message = response_json.get('message')
    if 200 != status:
        logging.error(f'状态码：{status}：{message}')
        raise QuarkError(status, message)
    return True


class QuarkError(Exception):

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class Api:

    def __init__(self, cookie: str) -> None:
        """
        初始化夸克网盘Api类
        :param cookie: 访问夸克网盘的cookie
        """
        self.headers = {
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'sec-ch-ua-mobile': '?0',
            'user-agent': UA,
            'sec-ch-ua-platform': '"macOS"',
            'origin': 'https://pan.quark.cn',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://pan.quark.cn/',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': cookie}

    def get_stoken(self, pwd_id: str):
        """
        获取夸克网盘的stoken
        :param pwd_id:夸克网盘分享链接的pwd_id
        :return:
        """
        url = f'https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token'
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": util.generate_timestamp()
        }
        payload = {"pwd_id": pwd_id, "passcode": ""}
        response = requests.post(url, params=params, json=payload, headers=self.headers).json()
        success(response)
        return response.get("data").get("stoken")

    def detail(self, pwd_id, stoken, page=1, pdir_fid=0):
        """
        获取分享链接文件详情
        :param pwd_id: 夸克网盘分享链接的pwd_id
        :param stoken: 夸克网盘分享链接的token
        :param page: 页数，默认第一页
        :param pdir_fid:父文件夹ID，默认为0，即根目录
        :return: 返回链接首层目录的所有文件信息列表
        """
        global data_list
        url = f"https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail"
        headers = self.headers
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": pdir_fid,
            "force": 0,
            "_page": page,
            "_size": "50",
            "_fetch_banner": 1,
            "_fetch_share": 1,
            "_fetch_total": 1,
            "_sort": "file_type:asc,file_name:asc",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": util.generate_timestamp()
        }
        response = requests.get(url, headers=headers, params=params).json()
        success(response)
        id_list = response.get("data").get("list")
        total = response.get("metadata").get("_total")
        return id_list, util.have_next_page(50, total, page)

    def task(self, task_id, trice=20):
        """
        根据task_id查询任务执行情况
        :param task_id:
        :param trice: 重试次数，默认重试20次
        :return: 成功后返回任务执行结果
        :raises: 抛出QuarkError，任务超时未完成
        """
        for i in range(trice):
            url = f"https://drive-pc.quark.cn/1/clouddrive/task"
            params = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "task_id": task_id,
                "retry_index": i,
                "__dt": int(random.uniform(1, 5) * 60 * 1000),
                "__t": util.generate_timestamp(13)
            }
            response = requests.get(url, headers=self.headers, params=params).json()
            success(response)
            if response.get('data').get('status'):
                return response
            time.sleep(3)
        raise QuarkError(200, "任务超时")

    def save_task_id(self, pwd_id, stoken, file_ids, share_fid_tokens, to_pdir_fid=0):
        """
        创建保存链接任务，并获取任务ID
        :param pwd_id: 夸克网盘分享链接的pwd_id
        :param stoken: 夸克网盘分享链接的token
        :param file_ids: 需要分享的文件id
        :param share_fid_tokens: 需要分享的文件token
        :param to_pdir_fid: 保存目标目录
        :return: 返回任务ID，可通过task接口查询任务执行状态
        """
        url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": util.generate_timestamp(13)
        }
        data = {"fid_list": file_ids,
                "fid_token_list": share_fid_tokens,
                "to_pdir_fid": to_pdir_fid, "pwd_id": pwd_id,
                "stoken": stoken, "pdir_fid": 0, "scene": "link"}
        response = requests.post(url, json=data, headers=self.headers, params=params).json()
        success(response)
        task_id = response.get('data').get('task_id')
        return task_id

    def share_task_id(self, file_ids, file_name):
        """
        创建分享任务，并获取任务ID
        :param file_ids: 分享文件ID数组
        :param file_name: 分享标题名称
        :return: 返回分享任务ID
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/share"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": ""
        }
        data = {"fid_list": file_ids,
                "title": file_name,
                "url_type": 1, "expired_type": 1}
        response = requests.post(url, json=data, headers=self.headers, params=params).json()
        try:
            success(response)
        except QuarkError as e:
            logging.error(e.message)
            if e.status == 41029:
                forbidden_ms = response.get('metadata').get('share_control').get('forbidden_to')
                dt = datetime.datetime.fromtimestamp(forbidden_ms / 1000)
                logging.error('分享功能受限，限制到：' + dt.strftime('%Y-%m-%d %H:%M:%S'))
                time.sleep((forbidden_ms - datetime.time.microsecond) / 1000 + 5)
            else:
                raise e
        task_id = response.get("data").get("task_id")
        return task_id

    def get_share_link(self, share_id):
        """
        获取分享链接
        :param share_id: 分享ID，通过share任务执行后，通过task接口获取
        :return: 分享链接
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/share/password"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": ""
        }
        data = {"share_id": share_id}
        response = requests.post(url=url, json=data, params=params, headers=self.headers).json()
        success(response)
        return response.get("data").get("share_url")

    def new_dir(self, file_name, pdir_fid="0"):
        """
        新建文件夹
        :param file_name: 新建文件夹名称
        :param pdir_fid: 上级文件夹ID
        :return: 新建文件夹id
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/file"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": ""
        }
        data = {"dir_init_lock": False,
                "dir_path": "",
                "file_name": file_name,
                "pdir_fid": pdir_fid}
        response = requests.post(url, json=data, headers=self.headers, params=params).json()
        success(response)
        fid = response.get("data").get("fid")
        return fid

