

## 案例



```python

from cpan123 import Pan123OpenAPI

cpan = Pan123OpenAPI()
info = cpan.user.get_user_info()
log.info(f"用户信息: {info}")



file_path = "/downloads"
info = cpan.downloader.download(file_path, "./downloads_test")
log.info(f"下载信息: {info}")
```