from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()

share_baseurl = "https://www.123pan.com/s/"  # 分享链接的基础URL


def test_share():
    ## 先存一份数据到本地
    # file_list = pan123.file.list_v2(0, 10, "国科")
    # print(file_list.data)
    share = pan123.share.create(
        shareName="测试分享", shareExpire=1, fileIDList="11890750,12002051", skip=True
    )

    # 分享码,请将分享码拼接至 https://www.123pan.com/s/ 后面访问,即是分享页面
    print("----" * 10)
    assert share.data, "创建分享链接失败"
    print(share.data)
    print("分享链接:", share_baseurl + share.data["shareKey"])

    share2 = pan123.share.create(
        shareName="测试分享2", shareExpire=1, fileIDList="12004728,12004738", skip=True
    )

    print("----" * 10)
    assert share2.data, "创建分享链接失败"
    print(share2.data)
    print("分享链接2:", share_baseurl + share2.data["shareKey"])

    share3 = pan123.share.info(
        shareIdList=[share2.data["shareID"]],
        trafficSwitch=1,
        trafficLimitSwitch=1,
        trafficLimit=1000000,
    )
    print("----" * 10)
    print(f"修改分享链接: \n{share3.data}")

    # 获取分享链接信息
    res = pan123.share.list(limit=10, lastShareId=0)
    print("----" * 10)
    print(f"获取分享链接: \n{res.data}")


if __name__ == "__main__":
    test_share()
