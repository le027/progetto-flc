# MCP Client – Avvio e utilizzo

Questo client Python permette di collegarsi a un **server MCP (Model Context Protocol)** avviato localmente (il server può essere .py .js .csproj) e di interagire con i tool che il server espone.

Il client avvia automaticamente il server come processo figlio e gestisce la comunicazione MCP.

---

## Requisiti

- **Python 3.9 o superiore**

---

## Dipendenze Python

Prima di avviare il client, è necessario installare le dipendenze Python indicate di seguito.

### Dipendenza obbligatoria

```bash
pip install mcp
pip install anthropic python-dotenv
```

## Avvio del client

```bash
python3 client.py /ABSOLUTE/PATH/TO/serverMcp.csproj
```
