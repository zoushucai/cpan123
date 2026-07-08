import sys
from pathlib import Path

import click

from . import Pan123OpenAPI


class AliasedGroup(click.Group):
    """A click Group that supports registering aliases for commands and
    shows each command once in help with its aliases listed in parentheses.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases: dict[str, str] = {}

    def add_alias(self, alias: str, command_name: str) -> None:
        self._aliases[alias] = command_name

    def get_command(self, ctx, cmd_name):
        # First try normal lookup
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        # Then try aliases mapping
        real = self._aliases.get(cmd_name)
        if real:
            return super().get_command(ctx, real)
        return None

    def list_commands(self, ctx):  # noqa: ARG002
        # Only list real commands (no duplicate alias names)
        return sorted(self.commands.keys())

    def format_commands(self, ctx, formatter):
        """Customize the help output to show aliases next to command name."""
        commands = []
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is None:
                continue
            # collect aliases that map to this command
            aliases = [a for a, real in self._aliases.items() if real == name]
            display = f"{name} ({', '.join(aliases)})" if aliases else name
            commands.append((display, cmd.get_short_help_str()))

        if commands:
            with formatter.section("Commands"):
                formatter.write_dl(commands)


@click.group(cls=AliasedGroup)
@click.option(
    "-e",
    "--env",
    "envpath",
    type=click.Path(),
    default=None,
    envvar="CPAN123_ENV",
    help="指定 .env 路径（也可用环境变量 CPAN123_ENV）",
)
@click.pass_context
def cli(ctx, envpath):
    """Pan123 CLI 工具"""
    ctx.ensure_object(dict)
    ctx.obj["envpath"] = envpath


@cli.command("download")
@click.argument("remote_path", type=str)
@click.option("-o", "--output", type=click.Path(), default=None, help="本地保存路径/目录（可选）")
@click.option("--overwrite", is_flag=True, default=False, help="覆盖已存在的本地文件")
@click.pass_context
def download_cmd(ctx, remote_path, output, overwrite):
    """自动识别云端路径是文件或文件夹并下载。"""
    envpath = (ctx.obj or {}).get("envpath")
    client = Pan123OpenAPI(envpath=envpath)
    res = client.downloader.download(remote_path, local_path=output, overwrite=overwrite)
    if res is None:
        click.echo(f"下载失败或路径不存在: {remote_path}")
        raise SystemExit(1)
    # 如果是单文件返回 local_path
    if isinstance(res, dict) and res.get("local_path"):
        click.echo(f"下载成功: {res.get('local_path')}")
    else:
        # 文件夹下载返回统计信息
        click.echo(
            f"下载完成: {res.get('succeeded', 0)} 成功, {res.get('failed', 0)} 失败, 本地路径: {res.get('local_path')}"
        )
    return None


@cli.command("upload")
@click.argument("local_path", type=click.Path(exists=True), metavar="<文件路径>")
@click.option("-p", "--parent", type=int, default=0, show_default=True, help="云端目标目录 ID")
@click.option(
    "-d",
    "--dup",
    type=int,
    default=1,
    show_default=True,
    help="同名文件策略: 1=保留,2=覆盖",
)
@click.option(
    "-c",
    "--dir",
    "containDir",
    is_flag=True,
    default=True,
    show_default=True,
    help="包含本地目录结构",
)
@click.pass_context
def upload_cmd(ctx, local_path, parent, dup, containDir):
    """上传本地文件或目录到云端。会根据 local_path 自动判定文件或文件夹。"""
    envpath = (ctx.obj or {}).get("envpath")
    client = Pan123OpenAPI(envpath=envpath)
    path = Path(local_path)
    try:
        dup = 1 if dup == 1 else 2
        result = client.uploader.upload(
            path,
            parentFileID=parent,
            duplicate=dup,
            contain_dir=containDir,
            method="chunked",
        )
        total = int(result.get("total", 0) or 0)
        succeeded = int(result.get("succeeded", 0) or 0)
        failed = int(result.get("failed", 0) or 0)

        click.echo(f"上传完成: {path} --> parent: {parent}")
        click.echo(f"总数: {total}, 成功: {succeeded}, 失败: {failed}")

        if failed:
            data = result.get("data") or {}
            for file_path, detail in data.items():
                if not isinstance(detail, dict) or detail.get("success", True):
                    continue
                click.echo(f"失败: {file_path} -> {detail.get('message', 'unknown error')}")
            sys.exit(1)
        return None
    except Exception as e:
        click.echo(f"上传失败: {e}")
        sys.exit(1)


cli.add_alias("down", "download")

cli.add_alias("up", "upload")

if __name__ == "__main__":
    cli()
