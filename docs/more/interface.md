
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

- 采用`json5`的方式读入, 因此可以写注释. 

- 对应的json文件接口的实现, 引入了一些额外的字段:
	- `schema_` : 是对接口返回值的描述, 用于验证返回值的正确性, 验证响应数据中的 `data` 字段是否符合这个描述,  完全依靠 jsonschema 的语法. 由于 123 网盘返回的格式比较统一, 因此这里只验证 `data` 下的字段即可. 这样编写 jsonschema 简单一些.
	- `response_schema` : 是对接口返回值的描述, 用于验证返回值的正确性(与上面的区别,在于这个是简单的验证,只要返回的字段中存在指定的key, 就可以了)
	- `comment` : 是对接口的描述,无意义(后续会被过滤掉)

- 只能包含以下字段: `method`, `url`, `data`, `params`, `schema_`, `comment`, `response_schema`, `files` 

- 如果`data` 和 `params` 的值中有 `list` 或者 `dict`, 会使用 `json5.dumps` 转换成字符串.

	
一般字段后面会跟有值来解释和说明其参数的类型, 类似 jsonschema语法, 为什么不采用jsonschema呢? 因为jsonschema的语法太复杂了, 这里采用简化版的语法, 只需要知道类型和是否必须即可, 例如:

```json
"parentFileId": "number: required",
```

还可以跟个默认值, 语法如下 (注意分隔符是 `: ` 而不是 `:`, 中间有空格):

```
default: tpye: optional/required

参数:
	default: 默认值
	type: 类型
	optional: 可选 或者 required: 必须
```

如果只给出一个分割符, 会根据类型自动判断默认值,实在找不到,就是字符串类型
```
type: optional
# 或者
: type: required
```

如果直接写的字符串, 数字字符串, 布尔值, 则会做默认值处理, 类型为字符串
```json
"parentFileId": "123",
```

如果一个参数是必选的, 可以直接写成(类型都可以省略, 如果这个参数没有传递,则会报错)
```json
"parentFileId": ": required",
```

还可以在值中引入模板, (会在环境变量中查找, 如果没有找到, 则保留原值, 后续会被 `Auth` 类中的属性替换成对应的值. )

```json
"parentFileId": "{{ parentFileId }}",
```




### 举例

- 下面是获取文件列表的接口的json文件, 其中 `list_v2`是接口的名称, 其余为参数
	- `method`是请求方式, 
	- `url`是请求的url, 
	- `params`是请求参数, 
	- `schema_`是返回值的描述, 
	- `comment`是对接口的描述, 



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
        limit: int = 100,
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
		...
		...
```