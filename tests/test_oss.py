import random
from pathlib import Path

from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()


def test_oss_upload():
    imgfiles = [
        f
        for f in Path("assets").glob("*")
        if f.is_file() and f.suffix in [".jpg", ".png", ".webp"]
    ]

    imgfile = random.choice(imgfiles)
    print(f"Uploading {imgfile}")

    # imgfile = "assets/0a75f78d9e_亮元周患脖.png"
    res = pan123.upload_oss(imgfile, Path(imgfile).name)
    print(res)
    # 获取图片列表
    res = pan123.oss.list()
    print("----" * 10)
    print("获取图片列表")
    print(res.data)
    # 获取图片的详情
    res = pan123.oss.detail(
        fileID="yk6baz03t0l000d7w33fdduneewjjdg7DIYPAIiOAIaOAvx0DwF="
    )
    print("----" * 10)
    print("获取图片详情")
    print(res)
