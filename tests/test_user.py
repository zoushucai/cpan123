from cpan123 import Pan123openAPI

pan123 = Pan123openAPI()
print("----" * 10)
print(pan123.auth)


def test_user():
    # 获取用户信息
    user_info = pan123.user.info(skip=True)
    print("----" * 10)
    print(f"获取用户信息: \n{user_info.data}")
