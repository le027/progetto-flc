https://modelcontextprotocol.io/docs/develop/build-server


System requirements
.NET 8 SDK or higher installed.

# Add the Model Context Protocol SDK NuGet package
dotnet add package ModelContextProtocol --prerelease
# Add the .NET Hosting NuGet package
dotnet add package Microsoft.Extensions.Hosting

nel client come da tutorial Claude Desktop va inserita la configurazione del server (in questo caso hostato in locale)


code $env:AppData\Claude\claude_desktop_config.json
comando per creare nella cartella appdata di Claude un file di configurazione, il comando code permette di aprirlo in editing
direttamente in visual studio. Utilizza la var d'ambiente per ricavarsi il path
Contenuto:

{
  "mcpServers": {
    "weather": {
      "command": "dotnet",
      "args": [
        "run",
        "--project",
        "C:\\ABSOLUTE\\PATH\\TO\\PROJECT",  
        "--no-build"
      ]
    }
  }
}

Claude per richieste di tipo weather richiamerò le api esposte dal server mcp, il quale verrà avviato all'occorenza
automaticamente da claude