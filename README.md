# Factory AI Skills Installer

Instalador corporativo para descargar e instalar `ace-skill` en agentes de IA
que soporten archivos `SKILL.md`. Funciona en Windows, Linux, macOS y WSL.

> [!IMPORTANT]
> La herramienta instala los archivos en rutas compatibles conocidas. La carga
> efectiva depende de la versión y configuración de cada agente. El instalador
> verifica los archivos, pero no puede garantizar universalmente que cualquier
> IA cargue la skill.

## Índice

- [1. Qué hace](#1-qué-hace)
- [2. Fuente oficial](#2-fuente-oficial)
- [3. Requisitos](#3-requisitos)
- [4. Guía desde cero](#4-guía-desde-cero)
- [5. Comandos disponibles](#5-comandos-disponibles)
- [6. Agentes y `agents.yaml`](#6-agentes-y-agentsyaml)
- [7. Verificación funcional](#7-verificación-funcional)
- [8. Actualización](#8-actualización)
- [9. Solución de problemas](#9-solución-de-problemas)
- [10. Seguridad y límites](#10-seguridad-y-límites)
- [11. Pruebas de mantenimiento](#11-pruebas-de-mantenimiento)

## 1. Qué hace

La herramienta:

1. Comprueba Git y el acceso al repositorio privado.
2. Confirma la rama oficial `feat/ace-msgflow-emf`.
3. Descarga únicamente `skills/ace-skill` mediante sparse checkout.
4. Registra el commit exacto utilizado.
5. Detecta agentes compatibles y sus rutas configuradas.
6. Instala la skill de forma temporal y atómica.
7. Verifica el hash del contenido instalado.
8. Genera `.factory-skill-install.json` con la procedencia.
9. Evita sobrescribir una versión distinta sin `--update`.
10. Diagnostica el computador con `--doctor`.

La herramienta no almacena credenciales, no ejecuta código descargado desde la
skill y no reinicia aplicaciones del usuario.

## 2. Fuente oficial

| Dato | Valor |
|---|---|
| Repositorio | `https://dev.azure.com/SOAINTCORP/UENCDT%20Interop%20Gamma/_git/oia-api` |
| Rama | `feat/ace-msgflow-emf` |
| Carpeta | `skills/ace-skill` |
| Archivo obligatorio | `skills/ace-skill/SKILL.md` |

La ejecución normal no reemplaza la fuente remota por una copia local. Si el
repositorio, la rama o la ruta no están disponibles, la instalación se detiene.

## 3. Requisitos

Se necesita:

- Windows 10/11, Linux, macOS o WSL.
- Python 3.10 o superior.
- Git.
- Acceso a Azure DevOps y VPN corporativa cuando corresponda.
- Permiso de lectura sobre `oia-api` y la rama indicada.
- Un agente que soporte `SKILL.md` o una ruta personalizada documentada.

No se necesitan `pip`, `PyYAML`, entornos virtuales ni paquetes adicionales de
Python.

### 3.1 Windows

Instale Python y Git usando los canales autorizados por su organización. Python
puede descargarse desde <https://www.python.org/downloads/windows/> y Git desde
<https://git-scm.com/download/win>.

Después de instalar, cierre y abra PowerShell y verifique:

```powershell
python --version
git --version
```

Si `python` no está disponible:

```powershell
py -3 --version
```

PowerShell ya viene incluido en Windows. No se necesita `sh` para utilizar
`install.ps1` o `install.cmd`.

### 3.2 Linux Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y python3 git
python3 --version
git --version
sh --version
```

### 3.3 macOS

Si faltan las herramientas de línea de comandos:

```bash
xcode-select --install
```

Si Homebrew está autorizado:

```bash
brew install python git
python3 --version
git --version
sh --version
```

### 3.4 WSL

WSL tiene su propio `HOME`. Python y Git deben instalarse dentro de la
distribución WSL aunque estén instalados en Windows.

Desde PowerShell, si la política corporativa lo permite:

```powershell
wsl --install
```

Dentro de la distribución Linux:

```bash
sudo apt update
sudo apt install -y python3 git
python3 --version
git --version
```

## 4. Guía desde cero

### Paso 1: obtener el instalador

Clone o descargue el repositorio `factory-ai-skills-installer` por el método
autorizado por su organización:

```bash
git clone "<URL_DEL_REPOSITORIO_FACTORY-AI-SKILLS-INSTALLER>"
```

Entre en la carpeta descargada.

Windows PowerShell:

```powershell
Set-Location "C:\ruta\factory-ai-skills-installer"
```

Linux, macOS o WSL:

```bash
cd "/ruta/factory-ai-skills-installer"
```

Confirme que existen `install.ps1`, `install.cmd`, `install.sh`,
`install_skills.py` y `agents.yaml`.

### Paso 2: revisar el computador

`--doctor` es un diagnóstico local. No descarga la skill, no modifica archivos
y no necesita acceso a Azure DevOps.

Windows:

```powershell
python install_skills.py --doctor
```

Si es necesario:

```powershell
py -3 install_skills.py --doctor
```

Linux, macOS o WSL:

```bash
python3 install_skills.py --doctor
```

El diagnóstico muestra Python, Git, agentes detectados, versiones disponibles,
rutas, estado de `ace-skill`, hash, compatibilidad, reinicio requerido y
validaciones pendientes.

Para generar un reporte de soporte:

```bash
python install_skills.py --doctor --json > doctor-report.json
```

Revise el reporte antes de compartirlo, porque puede incluir rutas del usuario y
versiones del equipo.

### Paso 3: validar acceso a Azure DevOps

Conéctese a la VPN si corresponde y ejecute:

```bash
git ls-remote --exit-code --heads "https://dev.azure.com/SOAINTCORP/UENCDT%20Interop%20Gamma/_git/oia-api" "refs/heads/feat/ace-msgflow-emf"
```

Debe aparecer un commit seguido de:

```text
refs/heads/feat/ace-msgflow-emf
```

Si se solicita autenticación, use Git Credential Manager o el mecanismo
corporativo aprobado. No escriba contraseñas ni tokens en comandos o archivos.

### Paso 4: simular

La simulación valida acceso, rama y `SKILL.md`, pero no copia archivos.

Windows:

```powershell
python install_skills.py --dry-run
```

Linux, macOS o WSL:

```bash
python3 install_skills.py --dry-run
```

`WOULD-INSTALL` permite continuar. `OUTDATED` requiere revisar la instalación
existente. `CONFLICT` indica una carpeta que no parece una skill válida.

### Paso 5: instalar

Windows:

```powershell
.\install.ps1
```

También puede utilizar:

```powershell
.\install.cmd
```

Linux, macOS o WSL:

```bash
chmod +x install.sh
./install.sh
```

La herramienta descarga la skill desde `oia-api`, rama
`feat/ace-msgflow-emf`, registra el commit y verifica la instalación final.

### Paso 6: verificar y reiniciar

Vuelva a ejecutar:

```bash
python install_skills.py --doctor
```

Busque `skill instalada`, `hash verificado`, el commit y la ruta correcta.

Cierre completamente el agente, confirme que el proceso terminó y vuelva a
abrirlo. Las skills normalmente se cargan al iniciar una sesión nueva.

## 5. Comandos disponibles

| Comando | Uso |
|---|---|
| `--doctor` | Diagnostica el computador sin descargar ni modificar archivos |
| `--doctor --json` | Genera el diagnóstico en JSON |
| `--dry-run` | Simula la descarga e instalación |
| `--update` | Reemplaza una instalación diferente después de revisarla |
| `--target auto` | Instala en `.agents` y agentes detectados; es el valor predeterminado |
| `--target all` | Instala en todos los agentes definidos en `agents.yaml` |
| `--target AGENTE` | Instala en un agente específico; se puede repetir |
| `--dest RUTA` | Instala en una ruta personalizada documentada |
| `--list-targets` | Lista los agentes definidos en `agents.yaml` |
| `--json` | Devuelve el resultado de instalación en JSON |
| `--version` | Muestra la versión del instalador |

Ejemplos:

```bash
python install_skills.py --target opencode --target claude
python install_skills.py --target all
python install_skills.py --dest "/ruta/documentada/de/skills"
python install_skills.py --version
```

No invente rutas para `--dest`. Consulte primero la documentación oficial del
agente.

## 6. Agentes y `agents.yaml`

Los destinos se mantienen en `agents.yaml`. Para agregar un agente nuevo, se
debe modificar únicamente ese archivo, siempre que use una ruta compatible con
`SKILL.md`. No es necesario modificar `install_skills.py` para una configuración
básica nueva.

El archivo utiliza sintaxis JSON compatible con YAML para evitar dependencias
adicionales de Python. Sus campos son:

| Campo | Descripción |
|---|---|
| `relative_path` | Ruta relativa dentro del HOME del usuario |
| `detection_paths` | Carpetas que permiten detectar el agente |
| `executables` | Ejecutables que permiten detectarlo en `PATH` |
| `status` | `supported`, `conditional` o `unsupported` |
| `requires_restart` | Si requiere reiniciar el agente |
| `verification` | `filesystem` o `manual` |

Destinos actuales:

| Agente | Ruta | Soporte | Verificación |
|---|---|---|---|
| Agent Skills | `~/.agents/skills` | `supported` | Archivos |
| Claude Code | `~/.claude/skills` | `supported` | Archivos |
| OpenCode | `~/.config/opencode/skills` | `supported` | Archivos |
| OpenAI Codex | `~/.codex/skills` | `conditional` | Manual |
| Gemini CLI | `~/.gemini/skills` | `conditional` | Manual |
| Cursor | `~/.cursor/skills` | `conditional` | Manual |
| GitHub Copilot | `~/.copilot/skills` | `conditional` | Manual |

Después de editar `agents.yaml`:

```bash
python install_skills.py --list-targets
python -m unittest discover -s tests -v
```

## 7. Verificación funcional

Después de reiniciar el agente, abra una sesión nueva y escriba:

```text
Usando ace-skill, explícame qué archivos necesito para generar un desarrollo
base IBM ACE y cómo se selecciona una plantilla IBS, HUB u ORQ. No generes código.
```

La respuesta debe mencionar como mínimo:

- `SCI.md` y `ETI.md` obligatorios.
- Selector exacto en el encabezado del ETI.
- Plantillas `IBS`, `HUB` y `ORQ`.
- Copybook obligatorio solo para backend `IBS_RPG`.
- Uso de `BLOQUEO` cuando falta información obligatoria.

El instalador confirma archivos e integridad. La carga efectiva dentro de cada
IA debe confirmarse manualmente.

## 8. Actualización

Primero revise la instalación:

```bash
python install_skills.py --doctor
```

Después actualice solo si reconoce la versión existente:

Windows:

```powershell
.\install.ps1 --update
```

Linux, macOS o WSL:

```bash
./install.sh --update
```

La herramienta no sobrescribe silenciosamente una versión diferente. La
actualización utiliza una copia temporal y restaura la instalación anterior si
falla antes de finalizar.

## 9. Solución de problemas

| Error o síntoma | Causa probable | Solución |
|---|---|---|
| Python no está instalado | Python no está en `PATH` | Instalar Python 3.10+ o usar `py -3` en Windows |
| Git no está instalado | Git no está disponible | Instalar Git o solicitarlo al soporte |
| `Authentication failed` | Sesión, permisos o VPN | Conectarse a VPN y renovar Git Credential Manager |
| La rama no existe | Rama o permisos incorrectos | Confirmar `feat/ace-msgflow-emf` y acceso a `oia-api` |
| `SKILL.md` no existe | Ruta o rama incompleta | Detenerse y solicitar corrección del repositorio |
| `OUTDATED` | Existe otra versión | Revisar y usar `--update` si corresponde |
| `CONFLICT` | La carpeta contiene otros archivos | Hacer backup y revisar manualmente |
| La IA no usa la skill | Sesión antigua o ruta no soportada | Reiniciar, confirmar la ruta y repetir la prueba funcional |
| `hash no verificado` | Falta comprobante o hubo cambios | Reinstalar desde la fuente oficial |
| Agente no detectado | App gráfica o sin ejecutable en `PATH` | Usar `--target` o `--dest` con una ruta oficial |
| Error al leer `agents.yaml` | Configuración inválida | Revisar tipos, rutas relativas y valores permitidos |

Si el problema continúa, adjunte `doctor-report.json`, el mensaje completo y la
versión del instalador. No adjunte contraseñas, tokens ni certificados.

## 10. Seguridad y límites

- No almacena contraseñas ni tokens.
- Delega autenticación a Git y Git Credential Manager.
- No modifica configuraciones JSON de los agentes.
- No elimina una instalación diferente sin `--update`.
- No ejecuta archivos descargados desde `ace-skill`; solo los copia.
- Registra repositorio, rama, commit, fecha y hash.
- `--doctor` es local y no descarga archivos.
- No garantiza que una IA cargue la skill solo porque la carpeta exista.
- Windows y WSL pueden tener distintos `HOME` y distintas instalaciones.

## 11. Pruebas de mantenimiento

Ejecute las pruebas desde la raíz del repositorio:

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan carpetas temporales y no modifican las skills reales del
usuario. La pipeline `azure-pipelines.yml` ejecuta pruebas aisladas en:

- `windows-latest`
- `ubuntu-latest`
- `macOS-latest`

La pipeline valida la instalación idempotente, `--doctor`, `--list-targets`,
`install.ps1`, `install.cmd`, `install.sh` y las rutas temporales. No instala la
skill real en el HOME de los desarrolladores.
