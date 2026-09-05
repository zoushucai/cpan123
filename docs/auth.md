
## Auth 类

### 环境代理开关

`cpan123 0.2.15` 支持在认证使用的 `.env` 文件中配置 HTTPX 是否读取系统代理：

```dotenv
# true：读取 HTTP_PROXY、HTTPS_PROXY、ALL_PROXY 等环境变量（默认，兼容 0.2.14）
# false：忽略这些环境变量并直连
TRUST_ENV=true
```

未配置 `TRUST_ENV` 或值为空时默认为 `true`。JWT 和 OAuth 客户端都会使用该配置。




::: cpan123.authtype.Jwt



::: cpan123.Auth
