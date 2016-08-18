# 通用的mock server

## 请求示例:

`POST http://mocker:8888/create`

```json
{
  "path": "/echo",
  "method": "post",
  "mode": 1,
  "responses": [
    {
      "content": "{\"hello\": \"world\"}",
      "content_type": "application/json",
      "status_code": 200,
      "keyword": "world",
      "regular": null
    },
    {
      "content": "{\"foo\": \"bar\"}",
      "status_code": 200,
      "keyword": "foo",
      "regular": null,
      "headers": {
        "Auth": "1000000"
      }
    }
  ]
}
```

成功响应:

```json
{
  "msg": "ok"
}
```

## 模式说明:

mocker支持三种mock模式:

- 普通模式(`mode=0`): 即设定的接口返回固定的Response
- 关键字模式(`mode=1`): 会解析Request的字符串,根据预设好的关键字,返回特定的Response
- 正则模式(`mode=2`): 会解析Request的字符串,与预设好的正则表达式匹配,返回符合条件的Response
