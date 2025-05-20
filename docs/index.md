
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

### 使用

- 关于授权参考: [Auth](./more/auth.md)

- 使用方法参考: [Pan123openAPI](./more/pan.md)


### 个人主要用的三个功能已封装.

- [x] 上传文件(夹)
- [x] 下载文件(夹)
- [x] 上传图片到oss


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


## Bug 反馈

- 本人编程能力有限,程序可能会有bug,如果有问题请反馈

- 如果有好的建议,也欢迎反馈 [Issues](https://github.com/zoushucai/cpan123/issues)


