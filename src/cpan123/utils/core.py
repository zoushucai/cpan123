import os
import re
from typing import Any, Dict, Optional, Type, Union

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from .const import (
    DEFAULT_BY_TYPE,
    EMBEDDED_TEMPLATE_PATTERN,
    TEMPLATE_PATTERN,
    TYPE_MAP,
)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true")


@dataclass
class ParsedField:
    name: str
    type_: Type
    required: bool
    default: Any
    is_template: bool = False
    template_key: Optional[str] = None
    is_constant: bool = False

    model_config = ConfigDict(extra="forbid")


class FieldParser:
    SKIP_KEYS = {"comment", "schema_", "files", "headers", "auth", "response_schema"}

    @staticmethod
    def parse(name: str, raw_value: Any) -> ParsedField:
        if raw_value is None or (
            isinstance(raw_value, str)
            and any(x in raw_value.lower() for x in ("none", "null"))
        ):
            return ParsedField(
                name=name, type_=type(None), required=False, default=None
            )

        if not isinstance(raw_value, str):
            return ParsedField(
                name=name,
                type_=type(raw_value),
                required=False,
                default=raw_value,
                is_constant=True,
            )

        val = raw_value.strip()

        # {{ KEY }} 整体模板（环境变量）
        match = TEMPLATE_PATTERN.fullmatch(val)
        if match:
            return ParsedField(
                name=name,
                type_=str,
                required=False,
                default=os.getenv(match.group(1), f"{{{{ {match.group(1)} }}}}"),
                is_template=True,
                template_key=match.group(1),
            )

        # 嵌入式模板 {{{ key }}}
        if EMBEDDED_TEMPLATE_PATTERN.search(val):
            return ParsedField(
                name=name,
                type_=str,
                required=False,
                default=val,
                is_template=True,
                template_key=None,
            )

        # "default: type: required"
        parts = [p.strip() for p in val.split(": ")]
        if len(parts) == 3:
            default_str, type_str, required_str = parts

            required = required_str.lower() == "required"
            py_type_raw = TYPE_MAP.get(type_str.lower(), str)
            py_type = py_type_raw if isinstance(py_type_raw, type) else str

            default_value = default_str
            if default_str is not None:
                try:
                    if py_type is bool:
                        default_value = parse_bool(default_str)
                    else:
                        default_value = py_type(default_str)
                except Exception:
                    default_value = default_str
            elif required:
                default_value = None

            return ParsedField(
                name=name,
                type_=py_type,
                required=required,
                default=default_value,
            )

        elif len(parts) == 2:
            type_str, required_str = parts
            try:
                default_str = DEFAULT_BY_TYPE.get(type_str.lower(), "")
                type_ = TYPE_MAP.get(type_str.lower(), str)
                required = required_str.lower() == "required"
                return ParsedField(
                    name=name,
                    type_=type_,
                    required=required,
                    default=default_str,
                )
            except Exception as e:
                raise ValueError(f"无法解析字段: {name}, 值: {val}") from e

        elif len(parts) == 1:
            # 只有一个值，默认是字符串类型, 且不是必填, 认为是常量
            return ParsedField(
                name=name,
                type_=str,
                required=False,
                default=val,
                is_constant=True,
            )

        else:
            raise ValueError(f"无法解析字段: {name}, 值: {val}")

    @staticmethod
    def _replace_embedded_templates(value: str, context: Dict[str, Any]) -> str:
        def _resolve_key_path(context: Dict[str, Any], key_path: str) -> Any:
            keys = key_path.split(".")
            val = context
            for k in keys:
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    return f"{{{{{{ {key_path} }}}}}}"  # fallback 原样
            return val

        def replace_match(match: re.Match) -> str:
            key_path = match.group(1)
            return str(_resolve_key_path(context, key_path))

        return EMBEDDED_TEMPLATE_PATTERN.sub(replace_match, value)

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        parsed = {}
        for key, value in data.items():
            if key in FieldParser.SKIP_KEYS:
                continue

            if isinstance(value, dict):
                parsed[key] = FieldParser.parse_dict(value)
            else:
                parsed[key] = FieldParser.parse(key, value)

        return parsed

    @staticmethod
    def _resolve_template_value(field: ParsedField, context: Dict[str, Any]) -> Any:
        if field.is_template and isinstance(field.default, str):
            return FieldParser._replace_embedded_templates(field.default, context)
        return field.default

    @staticmethod
    def validate_and_fill_input(
        template: Dict[str, Union[ParsedField, dict]],
        user_input: Dict[str, Any],
        path: str = "",
    ) -> Dict[str, Any]:
        result = {}
        ## 添加特殊字段
        template["skip"] = ParsedField(
            name="skip",
            type_=bool,
            required=False,
            default=False,
            is_constant=True,
        )

        for key, field_or_nested in template.items():
            full_key = f"{path}.{key}" if path else key

            if isinstance(field_or_nested, dict):
                # 处理嵌套结构
                nested_result = {}
                for nested_key, nested_field in field_or_nested.items():
                    nested_full_key = f"{full_key}.{nested_key}"

                    if isinstance(nested_field, dict):
                        raise ValueError(f"暂不支持三层嵌套字段: {nested_full_key}")

                    if nested_key in user_input:
                        # 保留 None 值
                        nested_result[nested_key] = user_input[nested_key]
                    elif nested_field.required:
                        raise ValueError(f"缺少必填字段: `{nested_full_key}`")
                    else:
                        nested_result[nested_key] = FieldParser._resolve_template_value(
                            nested_field, user_input
                        )

                result[key] = nested_result

            else:
                # 顶级字段处理
                if key in user_input:
                    result[key] = user_input[key]
                elif field_or_nested.required:
                    raise ValueError(f"缺少必填字段: `{full_key}`")
                else:
                    result[key] = FieldParser._resolve_template_value(
                        field_or_nested, user_input
                    )

        # 特殊保留字段：直接覆盖模板中的默认值
        for special in FieldParser.SKIP_KEYS:
            if special in ["comment"]:
                continue
            if special in user_input:
                result[special] = user_input[special]

        return result
