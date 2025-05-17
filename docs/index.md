
## cpan123

这是一个非官方的123云盘开放平台调用库，可以轻松的在Python中调用123云盘开放平台而不需要多次编写重复的代码


- 已有的python库

    - [pan123](https://pypi.org/project/pan123/)

    - [123pan](https://github.com/wojiaoyishang/123pan)

优势:

- 主要对返回的结果做了类型检查, 防止网络异常等不知道什么情况下导致的错误

- 上传文件采用多线程.

- 下载文件采用第三方库, `pip install py3-wget`

吐槽:

- 123云盘有些时候抽风, 对于同一段代码, 有时候能成功, 有时候不能成功, 可能是网络问题, 也可能是123云盘的问题.
- 同一个文件在网盘上有多份, 有可能居然找不到? 不知道什么怎么回事.(感觉是123云盘抽风)


### 安装
```bash
pip install cpan123
```

### 授权


!!! note 
    建议使用环境变量, token和client_id 二选一即可.

    - PAN123TOKEN: 授权 token
    - PAN123TOKEN_EXPIREDAT: 授权 token 过期时间
    - PAN123CLIENTID: 客户端 ID
    - PAN123CLIENTSECRET: 客户端密钥


```python
# 方式1: 使用环境变量中的授权信息
from cpan123 import Pan123openAPI
pan123 = Pan123openAPI() 

# 方式2: 使用授权信息
from cpan123 import Pan123openAPI, Auth
auth = Auth(clientID="your_client_id", clientSecret="your_client_secret")
print(auth.access_token) # 打印 access_token

# 或者
auth = Auth(access_token="your_access_token")
print(auth.access_token) # 打印 access_token

# 然后传入 Pan123openAPI中
pan123 = Pan123openAPI(auth=auth)

```

### 使用

```python
from cpan123 import Pan123openAPI
from pathlib import Path

pan123 = Pan123openAPI()

# # 下载单个文件
fname = "xxxx.pt"
pan123.download(fname)

# # 下载多个文件
# filenames = ["xxxx1.pt", "xxx2.pt"]
# pan123.download(filenames)
# 上传文件
fname = "xxxxx.zip"
pan123.upload(fname, fname, 0, overwrite=True)
print("上传完成")

# 上传文件到oss(图床)
imgfile = "xxxx.png"
res = pan123.upload_oss(imgfile, Path(imgfile).name)
print(res)
```

- 推荐上传与下载的文件都在根目录下, 且是文件

- 如果一个文件在云端过多, 可能会出一定的bug, 我遇到过, 当同一个文件在云端回收站和根目录下都有时, 下载时会过滤, 结果发现找不到非回收站的文件. 猜测和缓存之类的有关



### 个人主要用的三个功能已封装.

- [x] 上传文件
- [x] 下载文件
- [x] 上传图片到oss

建议单个文件下载与上传, 暂不支持文件夹的上传与下载.

### 已实现的接口

- [x] 文件管理
- [x] 分享管理
- [x] 离线下载
- [x] 用户管理
- [x] 直链
- [x] 图床
- [ ] 视频转码
    - 容量需要单独购买, 目前不支持对接



## 参考: 

- [123云盘开放平台](https://123yunpan.yuque.com/org-wiki-123yunpan-muaork/cr6ced/ppsuasz6rpioqbyt)


