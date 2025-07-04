import sys
import typer
from typing_extensions import Annotated
from typing import Optional
from .core import OverleafClient

app = typer.Typer(help="Quick dev CLI around Overleaf–MCP operations")

# ---------- GENERIC WRAPPER HELPERS ----------


def _get_client(project: str) -> OverleafClient:
    try:
        return OverleafClient(project)
    except Exception as e:  # login failure, missing project, etc.
        typer.secho(f"ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


# ---------- COMMANDS ----------


@app.command()
def projects():
    """
    List all accessible Overleaf projects (name + id).
    """
    try:
        for p in OverleafClient.list_projects():
            typer.echo(f"{p['name']} (id={p['id']})")
    except Exception as e:
        typer.secho(f"Error listing projects: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def ls(
    project: Annotated[str, typer.Argument(help="Exact Overleaf project name")],
    path: Annotated[str, typer.Argument(help="Folder path, leave blank for root")] = "",
):
    """List directory contents."""
    client = _get_client(project)
    try:
        for ent in client.listdir(path):
            typer.echo(ent)
    except Exception as e:
        typer.secho(f"Error listing '{path}': {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def read(
    project: Annotated[str, typer.Argument()],
    file: Annotated[str, typer.Argument(help="File path (e.g. main.tex)")],
):
    """Read a file and print to stdout."""
    client = _get_client(project)
    try:
        typer.echo(client.read(file))
    except FileNotFoundError:
        typer.secho(f"File '{file}' not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def write(
    project: Annotated[str, typer.Argument()],
    file: Annotated[str, typer.Argument(help="File path to write")],
):
    """Write stdin → Overleaf file."""
    data = sys.stdin.read()
    if not data:
        typer.echo("No input on stdin → nothing written")
        raise typer.Exit()

    client = _get_client(project)
    try:
        client.write(file, data)
        typer.secho("Write OK", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


@app.command()
def create_file(
    project: Annotated[str, typer.Argument(help="Exact Overleaf project name")],
    file: Annotated[
        str, typer.Argument(help="Path to new file (relative to project root)")
    ],
    content: Annotated[
        Optional[str],
        typer.Option(help="Content for new file (optional, defaults to empty)"),
    ] = "",
):
    """
    Create a new file in an Overleaf project. Overwrites if exists.
    """
    client = _get_client(project)
    try:
        client.create_file(file, content or "")
        typer.secho(
            f"File '{file}' created in project '{project}'", fg=typer.colors.GREEN
        )
    except Exception as e:
        typer.secho(f"Error creating file: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def rm(
    project: Annotated[str, typer.Argument(help="Exact Overleaf project name")],
    file: Annotated[str, typer.Argument(help="Path to file/folder to remove")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Do not prompt before removal.")
    ] = False,
):
    """Remove a file or empty directory from an Overleaf project."""
    if not force:
        typer.confirm(f"Are you sure you want to delete '{file}'?", abort=True)

    client = _get_client(project)
    try:
        client.remove(file)
        typer.secho(f"Removed '{file}'", fg=typer.colors.GREEN)
    except FileNotFoundError:
        typer.secho(f"Error: File '{file}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error removing file: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def mkdir(
    project: Annotated[str, typer.Argument(help="Exact Overleaf project name")],
    path: Annotated[str, typer.Argument(help="Path of new directory to create")],
):
    """Create a new directory in an Overleaf project."""
    client = _get_client(project)
    try:
        client.mkdir(path)
        typer.secho(f"Directory '{path}' created.", fg=typer.colors.GREEN)
    except Exception as e:
        # The underlying API might throw an error if the path already exists
        typer.secho(f"Error creating directory: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
