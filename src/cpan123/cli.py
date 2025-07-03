from pathlib import Path

import click

from .pan import Pan123openAPI


@click.group()
def cli():
    """Pan123 CLI 工具"""
    pass


@cli.command()
@click.argument("filename", type=click.Path(exists=False))
@click.option("-u", "--onlyurl", is_flag=True, help="只获取下载链接")
@click.option("-o", "--overwrite", is_flag=True, help="覆盖已有文件")
def download(filename, onlyurl, overwrite):
    """下载文件"""
    pan = Pan123openAPI()
    try:
        result = pan.download(filename, onlyurl=onlyurl, overwrite=overwrite)
        if onlyurl:
            click.echo(result)
    except Exception as e:
        click.echo(f"下载失败: {e}", err=True)


@cli.command()
@click.argument("filename", type=click.Path(exists=True), metavar="<文件路径>")
@click.option("-n", "--name", type=str, help="上传后使用的文件名")
@click.option(
    "-p", "--parent", type=int, default=0, show_default=True, help="云端目标目录 ID"
)
@click.option("-o", "--overwrite", is_flag=True, help="覆盖同名文件")
@click.option(
    "-d", "--dup", type=click.Choice(["1", "2"]), help="同名文件策略: 1=保留,2=覆盖"
)
@click.option("-c", "--dir", "containDir", is_flag=True, help="包含本地目录结构")
def upload(
    filename: str, name: str, parent: int, overwrite: bool, dup: str, containDir: bool
):
    """上传文件到云盘"""
    pan = Pan123openAPI()
    try:
        file_id = pan.upload(
            filename=filename,
            upload_name=name,
            parentFileID=parent,
            overwrite=overwrite,
            duplicate=int(dup) if dup else None,
            containDir=containDir,
        )
        click.secho(f"✅ 上传完成，文件 ID: {file_id}", fg="green")
    except Exception as e:
        click.secho(f"❌ 上传失败: {e}", fg="red", err=True)


@cli.command()
@click.argument(
    "localdirs", type=click.Path(exists=True), nargs=-1, metavar="<目录路径...>"
)
@click.option("-r", "--root", type=int, default=0, help="云端目标根目录 ID")
def upload_dir(localdirs: tuple[str | Path], root: int = 0):
    """上传一个或多个目录到云盘"""
    pan = Pan123openAPI()
    try:
        for localdir in localdirs:
            path = Path(localdir).resolve()
            click.secho(f"📁 开始上传: {path}", fg="cyan")
            pan.upload_dir(local_dir=path, root_id=root)
        click.secho("✅ 所有目录上传完成", fg="green")
    except Exception as e:
        click.secho(f"❌ 目录上传失败: {e}", fg="red", err=True)


@cli.command()
@click.argument("dirnames", type=str, metavar="<目录路径，多个用逗号分隔>")
@click.option("-o", "--output", type=click.Path(), default=".", help="输出路径")
def download_dir(dirnames: str, output: str):
    """下载云盘目录，可以用逗号分隔多个目录"""
    pan = Pan123openAPI()

    # 支持多个目录路径（逗号分隔）
    dirname_list = [d.strip() for d in dirnames.split(",") if d.strip()]

    # 如果只有一个目录，就传单个字符串（让 API 更智能处理）
    dir_arg = dirname_list[0] if len(dirname_list) == 1 else dirname_list

    try:
        pan.download_dir(dirnames=dir_arg, output_path=output)
        click.secho("✅ 目录下载完成", fg="green")
    except Exception as e:
        click.secho(f"❌ 目录下载失败: {e}", fg="red", err=True)


if __name__ == "__main__":
    cli()
