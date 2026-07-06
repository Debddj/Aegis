import httpx
import typer

app = typer.Typer()

@app.command()
def inject(scenario: str, target: str = "http://localhost:8100"):
    r = httpx.post(f"{target}/_inject/{scenario}")
    print(r.json())

if __name__ == "__main__":
    app()
