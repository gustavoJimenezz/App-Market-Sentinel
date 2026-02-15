📋 Resumen de Instalación: GitHub MCP con Docker
1. Preparación de Seguridad (El archivo .env)
No escribimos el token directamente en el comando para evitar que quede en el historial.

Creamos un archivo .env en la carpeta del proyecto.

Agregamos: GITHUB_PAT=tu_token_ghp_aquí.

Protegemos el proyecto para no subir el secreto a la nube:

Bash
echo -e ".env\n.mcp.json" >> .gitignore
2. Permisos de Docker (Vital en Linux)
Para que Claude pueda usar Docker sin pedirte sudo constantemente, le dimos permisos a tu usuario:

Bash
sudo usermod -aG docker $USER
newgrp docker
Esto permite que Claude "levante" el contenedor del servidor de GitHub por sí solo.

3. Instalación del Servidor (El comando maestro)
Ejecutamos el comando que vincula a Claude con el contenedor oficial de GitHub:

Bash
claude mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=$(grep GITHUB_PAT .env | cut -d '=' -f2) -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server
4. Ciclo de Vida del MCP
Inicio: El contenedor de Docker solo existe mientras Claude Code está abierto.

Eficiencia: Al cerrar Claude (/exit), el contenedor se destruye automáticamente (--rm) para no consumir recursos.

Verificación: Para ver el proceso activo, debes usar docker ps en una terminal aparte mientras Claude está ejecutándose.

5. Uso de Herramientas
No hace falta nombrar el MCP al hablar.

Claude detecta el repositorio automáticamente mediante el comando git remote.

Solo le pides cosas como: "Crea un issue basado en este archivo" y él usará sus herramientas de GitHub.