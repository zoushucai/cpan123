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


if __name__ == "__main__":
    cli()
