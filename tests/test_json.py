import sys
from pathlib import Path
from typing import Dict

from pydantic import TypeAdapter

from cpan123.utils.checkdata import JsonInput


def test_json():
    import json5

    jsondir = Path("src/cpan123/apijson")
    jsonfiles = [f for f in jsondir.glob("*.json") if f.is_file()]
    for path in jsonfiles:
        with open(path, "r", encoding="utf-8") as file:
            try:
                data: dict = json5.load(file)
            except Exception as e:
                print(f"❌ JSON 解析失败: {path}\n错误: {e}")
                sys.exit(1)
        user_list_adapter = TypeAdapter(Dict[str, JsonInput])

        user_list_adapter.validate_python(data)
