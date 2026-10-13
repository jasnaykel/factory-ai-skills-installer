#!/usr/bin/env python3
"""Descarga e instala ace-skill en agentes de IA compatibles con SKILL.md."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.2.0"
DEFAULT_REPOSITORY = "https://dev.azure.com/SOAINTCORP/UENCDT%20Interop%20Gamma/_git/oia-api"
DEFAULT_BRANCH = "feat/ace-msgflow-emf"
DEFAULT_SKILL_PATH = "skills/ace-skill"
RECEIPT_NAME = ".factory-skill-install.json"
AGENTS_CONFIG = Path(__file__).with_name("agents.yaml")
IGNORED_NAMES = {".git", ".pytest_cache", "__pycache__", ".DS_Store", RECEIPT_NAME}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class Target:
    name: str
    relative_path: Path
    detection_paths: tuple[Path, ...] = ()
    executables: tuple[str, ...] = ()
    status: str = "conditional"
    requires_restart: bool = True
    verification: str = "manual"


def load_targets(config_path: Path = AGENTS_CONFIG) -> dict[str, Target]:
    """Load and validate agent destinations from the JSON-compatible YAML file."""
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"No se pudo leer la configuración de agentes: {config_path}: {error}"
        ) from error

    raw_agents = config.get("agents")
    if not isinstance(raw_agents, dict) or not raw_agents:
        raise RuntimeError(f"La configuración no contiene agentes válidos: {config_path}")

    valid_statuses = {"supported", "conditional", "unsupported"}
    valid_verifications = {"filesystem", "manual"}
    targets: dict[str, Target] = {}
    for name, raw in raw_agents.items():
        if not isinstance(raw, dict) or not isinstance(raw.get("relative_path"), str):
            raise RuntimeError(f"El agente '{name}' no tiene relative_path válido.")
        relative_path = Path(raw["relative_path"])
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"El agente '{name}' tiene una ruta relativa inválida.")

        for field in ("detection_paths", "executables"):
            value = raw.get(field, [])
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise RuntimeError(f"El agente '{name}' tiene {field} inválido; debe ser una lista de textos.")

        status = raw.get("status", "conditional")
        verification = raw.get("verification", "manual")
        requires_restart = raw.get("requires_restart", True)
        if status not in valid_statuses:
            raise RuntimeError(f"El agente '{name}' tiene status inválido: {status}")
        if verification not in valid_verifications:
            raise RuntimeError(f"El agente '{name}' tiene verification inválido: {verification}")
        if not isinstance(requires_restart, bool):
            raise RuntimeError(f"El agente '{name}' tiene requires_restart inválido; debe ser booleano.")

        targets[name] = Target(
            name,
            relative_path,
            tuple(Path(value) for value in raw.get("detection_paths", [])),
            tuple(raw.get("executables", [])),
            status,
            requires_restart,
            verification,
        )
    return targets


TARGETS = load_targets()


def ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def skill_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*") if path.is_file() and not ignored(path.relative_to(root))
    )


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in skill_files(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def copy_filter(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in IGNORED_NAMES or Path(name).suffix in IGNORED_SUFFIXES
    }


def target_detected(target: Target, home: Path) -> bool:
    if target.name == "agents":
        return True
    if any((home / path).exists() for path in target.detection_paths):
        return True
    return any(shutil.which(executable) for executable in target.executables)


def command_version(command: str) -> str | None:
    """Return a short executable version without failing the diagnostic."""
    executable = shutil.which(command)
    if not executable:
        return None
    result = run_git([executable, "--version"], f"la versión de {command}", timeout=10)
    if result.returncode != 0:
        return "detectado; versión no disponible"
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else "detectado; versión no disponible"


def doctor_report(home: Path) -> dict[str, object]:
    """Inspect the local machine without downloading or modifying files."""
    agents: list[dict[str, object]] = []
    for name, target in TARGETS.items():
        detected = target_detected(target, home)
        destination = home / target.relative_path
        skill = destination / "ace-skill"
        receipt_path = skill / RECEIPT_NAME
        receipt: dict[str, object] | None = None
        if receipt_path.is_file():
            try:
                loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    receipt = loaded
            except (OSError, json.JSONDecodeError):
                receipt = None

        installed = (skill / "SKILL.md").is_file()
        local_hash = tree_hash(skill) if installed else None
        receipt_hash = receipt.get("content_sha256") if receipt else None
        hash_verified = bool(local_hash and receipt_hash and local_hash == receipt_hash)
        validations: list[str] = []
        if not installed:
            validations.append("ace-skill no está instalada en esta ruta")
        if installed and not receipt:
            validations.append("no existe un comprobante de instalación válido")
        if installed and receipt and not hash_verified:
            validations.append("el hash local no coincide con el comprobante")
        if target.verification == "manual":
            validations.append("la carga efectiva requiere verificación manual en el agente")
        elif detected and installed:
            validations.append("la carga efectiva no se puede confirmar desde el instalador")

        executable_versions = {
            executable: command_version(executable)
            for executable in target.executables
            if shutil.which(executable)
        }
        agents.append(
            {
                "name": name,
                "detected": detected,
                "status": target.status,
                "verification": target.verification,
                "requires_restart": target.requires_restart and installed,
                "path": str(destination),
                "skill_installed": installed,
                "hash_verified_against_receipt": hash_verified,
                "installed_hash": local_hash,
                "commit": receipt.get("commit") if receipt else None,
                "executable_versions": executable_versions,
                "validations_not_performed": validations,
            }
        )

    return {
        "installer": "factory-ai-skills-installer",
        "installer_version": VERSION,
        "system": platform.system(),
        "release": platform.release(),
        "python": platform.python_version(),
        "git": command_version("git"),
        "home": str(home),
        "agents": agents,
    }


def print_doctor_report(report: dict[str, object]) -> None:
    print("Factory AI Skills Installer - Doctor")
    print(f"Sistema operativo: {report['system']} {report['release']}")
    print(f"Python: {report['python']}")
    print(f"Git: {report['git'] or 'no disponible'}")
    print(f"Home: {report['home']}")
    print("\nAgentes:")
    for agent in report["agents"]:
        state = "detectado" if agent["detected"] else "no detectado"
        installed = "instalada" if agent["skill_installed"] else "no instalada"
        verified = "hash verificado" if agent["hash_verified_against_receipt"] else "hash no verificado"
        print(f"- {agent['name']}: {state}; skill {installed}; {verified}")
        print(f"  Ruta: {agent['path']}")
        print(f"  Compatibilidad: {agent['status']}; verificación: {agent['verification']}")
        if agent["commit"]:
            print(f"  Commit instalado: {agent['commit']}")
        if agent["requires_restart"]:
            print("  Acción: reiniciar el agente")
        for validation in agent["validations_not_performed"]:
            print(f"  Pendiente: {validation}")


def resolve_destinations(args: argparse.Namespace, home: Path) -> list[tuple[str, Path]]:
    destinations: list[tuple[str, Path]] = []
    selected = args.target or ["auto"]

    if "all" in selected:
        names = list(TARGETS)
    elif "auto" in selected:
        names = [name for name, target in TARGETS.items() if target_detected(target, home)]
        names.extend(name for name in selected if name != "auto" and name not in names)
    else:
        names = selected

    for name in names:
        destination = home / TARGETS[name].relative_path
        item = (name, destination)
        if item not in destinations:
            destinations.append(item)

    for raw_path in args.dest:
        destination = Path(raw_path).expanduser().resolve()
        item = ("custom", destination)
        if item not in destinations:
            destinations.append(item)

    return destinations


def discover_skills(source: Path) -> list[Path]:
    if not source.is_dir():
        raise ValueError(f"No existe el directorio de skills: {source}")
    skills = sorted(path.parent for path in source.glob("*/SKILL.md"))
    if not skills:
        raise ValueError(f"No se encontraron skills con SKILL.md en: {source}")
    return skills


def run_git(
    command: list[str],
    operation: str,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Git excedió {timeout} segundos durante {operation}.") from error
    except OSError as error:
        raise RuntimeError(f"No se pudo ejecutar Git durante {operation}: {error}") from error


def download_skill(
    repository: str,
    branch: str,
    skill_path: str,
    workspace: Path,
) -> tuple[Path, str]:
    if not shutil.which("git"):
        raise RuntimeError("Git no está instalado o no está disponible en PATH.")

    reference = f"refs/heads/{branch}"
    access = run_git(
        ["git", "ls-remote", "--exit-code", "--heads", repository, reference],
        "la validación de acceso al repositorio",
        timeout=60,
    )
    if access.returncode != 0 or not access.stdout.strip():
        detail = access.stderr.strip() or "la rama no existe o las credenciales no tienen acceso"
        raise RuntimeError(
            "No se pudo acceder al repositorio o confirmar la rama "
            f"'{branch}'. Verifique VPN, red y credenciales de Azure DevOps. Detalle: {detail}"
        )

    checkout = workspace / "oia-api"
    clone_base = [
        "git",
        "clone",
        "--depth",
        "1",
        "--sparse",
        "--branch",
        branch,
        "--single-branch",
    ]
    clone = run_git(
        [*clone_base, "--filter=blob:none", repository, str(checkout)],
        "la descarga sparse del repositorio",
    )
    if clone.returncode != 0:
        shutil.rmtree(checkout, ignore_errors=True)
        clone = run_git(
            [*clone_base, repository, str(checkout)],
            "el segundo intento de descarga del repositorio",
        )
    if clone.returncode != 0:
        raise RuntimeError(
            "Git confirmó el acceso, pero no pudo clonar la rama. Detalle: "
            + (clone.stderr.strip() or "error de clonación sin detalle")
        )

    sparse = run_git(
        ["git", "-C", str(checkout), "sparse-checkout", "set", skill_path],
        "la selección de la carpeta de la skill",
    )
    if sparse.returncode != 0:
        raise RuntimeError(
            f"No se pudo obtener únicamente '{skill_path}'. Detalle: "
            + (sparse.stderr.strip() or "error de sparse-checkout sin detalle")
        )

    skill_root = checkout / Path(skill_path)
    if not (skill_root / "SKILL.md").is_file():
        raise RuntimeError(
            f"La rama '{branch}' es accesible, pero '{skill_path}/SKILL.md' no existe."
        )

    commit_result = run_git(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        "la obtención del commit",
    )
    if commit_result.returncode != 0:
        raise RuntimeError("No se pudo registrar el commit descargado.")
    return skill_root.parent, commit_result.stdout.strip()


def write_receipt(
    destination: Path,
    source_hash: str,
    provenance: dict[str, str],
) -> None:
    receipt = {
        "installer": "factory-ai-skills-installer",
        "installer_version": VERSION,
        "content_sha256": source_hash,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        **provenance,
    }
    (destination / RECEIPT_NAME).write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def install_skill(
    source: Path,
    destination: Path,
    *,
    update: bool,
    dry_run: bool,
    provenance: dict[str, str] | None = None,
) -> str:
    source_hash = tree_hash(source)
    skill_file = destination / "SKILL.md"
    provenance = provenance or {"source": "local"}

    if skill_file.exists():
        if tree_hash(destination) == source_hash:
            return "exists-verified"
        if not update:
            return "outdated"

    if destination.exists() and not skill_file.exists() and not update:
        return "conflict"

    if dry_run:
        return "would-update" if destination.exists() else "would-install"

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{source.name}-", dir=destination.parent))
    staged = temporary / source.name
    backup: Path | None = None

    try:
        shutil.copytree(source, staged, ignore=copy_filter)
        if not (staged / "SKILL.md").is_file():
            raise RuntimeError(f"La copia de {source.name} no contiene SKILL.md")
        if tree_hash(staged) != source_hash:
            raise RuntimeError(f"La copia temporal de {source.name} no coincide con el origen")
        write_receipt(staged, source_hash, provenance)

        if destination.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            backup = destination.with_name(f"{destination.name}.backup-{timestamp}")
            destination.replace(backup)

        staged.replace(destination)
        if tree_hash(destination) != source_hash:
            raise RuntimeError(f"La instalación final de {source.name} no coincide con el origen")
        if backup:
            shutil.rmtree(backup)
        return "updated-verified" if backup else "installed-verified"
    except Exception:
        if backup and backup.exists():
            if destination.exists():
                shutil.rmtree(destination, ignore_errors=True)
            backup.replace(destination)
        elif destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Instala skills corporativas en agentes de IA compatibles con SKILL.md.",
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    result.add_argument(
        "--target",
        action="append",
        choices=["auto", "all", *TARGETS],
        help="Destino: auto (predeterminado), all o un agente específico. Se puede repetir.",
    )
    result.add_argument(
        "--dest",
        action="append",
        default=[],
        help="Directorio de skills personalizado. Se puede repetir.",
    )
    result.add_argument("--update", action="store_true", help="Actualiza instalaciones existentes.")
    result.add_argument("--dry-run", action="store_true", help="Muestra acciones sin escribir archivos.")
    result.add_argument("--doctor", action="store_true", help="Diagnostica el PC sin descargar ni modificar archivos.")
    result.add_argument("--list-targets", action="store_true", help="Lista destinos soportados y termina.")
    result.add_argument("--json", action="store_true", help="Emite el resultado como JSON.")
    result.add_argument(
        "--repository",
        default=DEFAULT_REPOSITORY,
        help="URL del repositorio que contiene la skill.",
    )
    result.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help="Rama del repositorio desde la que se descargará la skill.",
    )
    result.add_argument(
        "--skill-path",
        default=DEFAULT_SKILL_PATH,
        help="Ruta de ace-skill dentro del repositorio.",
    )
    result.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    result.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    return result


def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.list_targets:
        for name, target in TARGETS.items():
            print(f"{name:10} ~/{target.relative_path.as_posix()}")
        return 0

    home = (args.home or Path.home()).expanduser().resolve()
    if args.doctor:
        report = doctor_report(home)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_doctor_report(report)
        return 0

    with tempfile.TemporaryDirectory(prefix="factory-ai-skills-") as temporary:
        try:
            if args.source:
                source = args.source.expanduser().resolve()
                commit = "local-source"
                provenance = {"source": "local", "source_path": str(source)}
            else:
                source, commit = download_skill(
                    args.repository,
                    args.branch,
                    args.skill_path,
                    Path(temporary),
                )
                provenance = {
                    "source": "git",
                    "repository": args.repository,
                    "branch": args.branch,
                    "commit": commit,
                    "skill_path": args.skill_path,
                }
            skills = discover_skills(source)
            destinations = resolve_destinations(args, home)
        except (ValueError, RuntimeError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2

        results: list[dict[str, str]] = []
        failures = 0
        for target_name, base in destinations:
            for skill in skills:
                destination = base / skill.name
                try:
                    status = install_skill(
                        skill,
                        destination,
                        update=args.update,
                        dry_run=args.dry_run,
                        provenance=provenance,
                    )
                    results.append(
                        {
                            "target": target_name,
                            "skill": skill.name,
                            "destination": str(destination),
                            "status": status,
                        }
                    )
                    if status in {"conflict", "outdated"}:
                        failures += 1
                except (OSError, RuntimeError) as error:
                    failures += 1
                    results.append(
                        {
                            "target": target_name,
                            "skill": skill.name,
                            "destination": str(destination),
                            "status": "error",
                            "error": str(error),
                        }
                    )

    if args.json:
        print(
            json.dumps(
                {
                    "system": platform.system(),
                    "home": str(home),
                    "source": provenance,
                    "results": results,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Sistema: {platform.system()} | Home: {home}")
        print(f"Fuente: {provenance.get('source')} | Commit: {commit}")
        for item in results:
            print(f"[{item['status'].upper():13}] {item['target']}: {item['destination']}")
            if "error" in item:
                print(f"  {item['error']}")
        if failures:
            print("Hay instalaciones desactualizadas o conflictos. Use --update después de revisarlas.")
        else:
            print("Integridad verificada. Cierre y vuelva a abrir el agente para cargar la skill.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
