
## 接口

所有的接口采用json文件存储, 一个文件对应一个类接口, 全部存储在 `src/cpan123/apijson` 中
```bash

src/cpan123/apijson
├── directlink.json
├── file.json
├── offline.json
├── oss.json
├── share.json
└── user.json
```

## 举例
- 官方的接口 : [获取文件列表](https://123yunpan.yuque.com/org-wiki-123yunpan-muaork/cr6ced/zrip9b0ye81zimv4)

- 对应的json文件接口的实现, 引入了一些额外的字段:
	- `schema_` : 是对接口返回值的描述, 用于验证返回值的正确性, 验证返回的data字段是否符合这个描述, 
	- `response_schema` : 是对接口返回值的描述, 用于验证返回值的正确性(与上面的区别,在于这个是简单的验证,只要返回的字段中存在指定的key, 就可以了)
	- `comment` : 是对接口的描述,无意义

- 只能包含以下字段: `method`, `url`, `data`, `params`, `schema_`, `comment`, `response_schema`


- 下面是获取文件列表的接口的json文件, 其中`list_v2`是接口的名称, `method`是请求方式, `url`是请求的url, `params`是请求参数, `schema_`是返回值的描述, `comment`是对接口的描述

- 采用json5的方式读入, 因此可以写注释.

- 其中 `params` 和`data` 的格式是一样的, 他们对应下面都是一个dict(没有可以为null或不写), 其值我们不关心,但是其key后续会被用到,应该和python的接口保持一致


```json
{
  ....

	"list_v2": {
		"method": "get",
		"url": "/api/v2/file/list",
		"params": {
			"parentFileId": "number: required",
			"limit": "number: required",
			"searchData": "string: optional",
			"searchMode": "number: optional",
			"lastFileId": "number: optional"
		},
		"schema_": {
			"type": "object",
			"properties": {
				"lastFileId": { "type": "number" },
				"fileList": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"fileId": { "type": "number" },
							"filename": { "type": "string" },
							"type": { "type": "number", "enum": [0, 1] },
							"etag": { "type": "string" },
							"size": { "type": "number" },
							"status": { "type": "number" },
							"parentFileId": { "type": "number" },
							"category": { "type": "number" }, //"enum": [0, 1, 2, 3] 实际情况可以出现5,而文档写的是0-4, 因此不要
							"trashed": { "type": "number", "enum": [0, 1] }
						},
						"required": ["fileId", "filename", "type", "size", "etag", "status", "parentFileId", "category", "trashed"]
					}
				}
			},
			"required": ["lastFileId", "fileList"]
		}
	},
  ....
}
```

只需要在python中引入即可

```python
# 引入必要的类

class File(BaseApiClient):
    def __init__(self, auth: Optional[Auth] = None) -> None:
        super().__init__(filepath="file", auth=auth) # 这里的filepath对应上面的json文件名,不需要后缀

		...
		...
		

    @auto_args_call_api("list_v2")
    def list_v2(
        self,
        parentFileId: int,
        limit: int = Field(default=100, gt=0, le=100),
        searchData: Optional[str] = None,
        searchMode: Optional[int] = 0,
        lastFileId: Optional[int] = None,
        skip: bool = False,
    ) -> DataResponse:  # type: ignore
        """获取文件列表(V2版本, v1弃用)

        Args:
            parentFileId (int): 文件夹ID,根目录传 0
            limit (int): 每页文件数量,最大不超过100
            searchData (str, optional):搜索关键字将无视文件夹ID参数. 将会进行全局查找
            searchMode (int, optional): 搜索模式,0:模糊搜索,1:精确搜索,默认为0
            lastFileId (int, optional): 翻页查询时需要填写
            skip (bool): 是否跳过响应数据的模式校验
        """
        # 这里的函数体根本不会执行, 因为被装饰器给劫持了, 返回的结果是装饰器的返回值,所以对参数进行校验无效
        # 如果要对参数进行校验,需要 Field 等参数校验方法
        # 默认已开启函数参数校验
        # 总结: 所以完全不用写函数体

		...
		...
```