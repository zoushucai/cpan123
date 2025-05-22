# tests/test_core.py

import os

import pytest

from cpan123.utils.core import FieldParser


def test_constant_int_parsing():
    field = FieldParser.parse("retries", 3)
    assert field.default == 3
    assert field.type_ is int
    assert field.is_constant


def test_simple_template_parsing(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    field = FieldParser.parse("api_key", "{{ API_KEY }}")
    assert field.is_template
    assert field.default == "secret123"
    assert field.template_key == "API_KEY"


def test_embedded_template_resolution():
    context = {"user": {"id": "u123"}}
    template = "data/{{{ user.id }}}/result"
    resolved = FieldParser._replace_embedded_templates(template, context)
    assert resolved == "data/u123/result"


def test_default_and_type_parsing():
    field = FieldParser.parse("enabled", "true: bool: required")
    assert field.required
    assert field.default is True
    assert field.type_ is bool


def test_field_with_type_only():
    field = FieldParser.parse("foo", "int: optional")
    assert field.default == 0
    assert field.type_ is int


def test_minimal_required_input_success():
    schema = {"method": "GET: str: required", "timeout": "3: int: optional"}
    parsed = FieldParser.parse_dict(schema)
    user_input = {"method": "POST"}
    result = FieldParser.validate_and_fill_input(parsed, user_input)
    assert result["method"] == "POST"
    assert result["timeout"] == 3


def test_missing_required_field_raises():
    schema = {"url": "str: required", "method": "GET: str: optional"}
    parsed = FieldParser.parse_dict(schema)
    with pytest.raises(ValueError, match=r"缺少必填字段: `url`"):
        FieldParser.validate_and_fill_input(parsed, {})


def test_nested_structure_with_required_field():
    schema = {"config": {"debug": "false: bool: optional", "host": "str: required"}}
    parsed = FieldParser.parse_dict(schema)
    result = FieldParser.validate_and_fill_input(parsed, {"host": "localhost"})
    assert result["config"]["host"] == "localhost"
    assert result["config"]["debug"] is False


def test_non_string_value_in_string_format_field():
    field = FieldParser.parse("count", "5: int: required")
    assert field.default == 5
    assert field.type_ is int


def test_type_cast_failure_fallbacks_to_str():
    # Deliberate type mismatch: "abc" to int should fallback
    field = FieldParser.parse("bad_int", "abc: int: optional")
    assert field.default == "abc"
    assert field.type_ is int  # Still int, but fallback str as value


def test_type_keyword_only_constant_field():
    field = FieldParser.parse("is_active", "bool")
    assert field.is_constant
    assert field.default == "bool"


def test_null_value_yields_none():
    field = FieldParser.parse("token", "null")
    assert field.default is None
    assert field.type_ is type(None)


def test_skip_keys_in_parse_dict():
    data = {
        "method": "GET: str: optional",
        "comment": "not parsed",
        "schema_": {},
        "files": [],
    }
    parsed = FieldParser.parse_dict(data)
    assert "method" in parsed
    assert "comment" not in parsed
    assert "schema_" not in parsed
    assert "files" not in parsed


def test_template_parsing():
    os.environ["MY_ENV_VAR"] = "12345"

    schema = {
        "api_key": "{{ MY_ENV_VAR }}",
        "timeout": "5: int: optional",
        "config": {
            "path": "default/path: str: optional",
            "enabled": "true: bool: required",
        },
    }

    parsed = FieldParser.parse_dict(schema)
    filled = FieldParser.validate_and_fill_input(parsed, {"enabled": True})

    assert filled["api_key"] == "12345"
    assert filled["timeout"] == 5
    assert filled["config"]["path"] == "default/path"
    assert filled["config"]["enabled"] is True


def test_embedded_template_parsing():
    template = {"url": "https://example.com/{{{ user.name }}}/info"}
    user_input = {"user": {"name": "Alice"}}
    parsed = FieldParser.parse_dict(template)
    filled = FieldParser.validate_and_fill_input(parsed, user_input)

    assert filled["url"] == "https://example.com/Alice/info"


def test_files():
    with open("图吧工具箱2409安装程序.exe", "rb") as f:
        chunk = f.read(1024 * 1024 * 10)

        files = [("file", ("part", chunk))]

        res = {
            "url": "/rest/2.0/pcs/superfile2",
            "path": "xxx",
            "method": "POST",
            "partseq": 1,
            "files": files,
        }
        parsed = FieldParser.parse_dict(res)
        filled = FieldParser.validate_and_fill_input(parsed, {"files": files})
        assert filled["url"] == "/rest/2.0/pcs/superfile2"
        assert filled["files"] == files, "文件上传失败"
