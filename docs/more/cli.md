
## cli命令

### 1. 安装

```bash
pip install cpan123
```
### 2. 使用
```bash
cpan123 [command] [options]
```
### 3. 命令列表

- 暂时只提供下面两个命令

```bash

cpan123 upload [options]  # 上传文件到123云盘
cpan123 download [options]  # 下载文件

cpan123 download-dir [options]  # 下载目录
cpan123 upload-dir [options]  # 上传目录到123云盘

```


帮助信息

```bash
cpan123 --help  # 查看所有命令的帮助信息
cpan123 upload --help  # 查看上传命令的帮助信息
cpan123 download --help  # 查看下载命令的帮助信息
cpan123 upload-dir --help  # 查看上传目录命令的帮助信息
cpan123 download-dir --help  # 查看下载目录命令的帮助信息
```




### 4. eg:

```bash
cpan123 download-dir /1panel,/backsync   #从云端下载目录到本地(多个目录用逗号分隔)
cpan123 upload-dir docs src  #把docs和src目录上传到云端

```
