# Plan de mejoras — Factory AI Skills Installer

## Objetivo

Evolucionar el instalador desde una herramienta que copia skills verificadas a
una herramienta corporativa que también informe con precisión la compatibilidad,
la detección y el estado de carga de cada agente de IA.

## Estado actual

- [x] Corregir la promesa conceptual de compatibilidad universal.
- [x] Documentar que la instalación de archivos no garantiza la carga por parte del agente.
- [x] Mantener la rama oficial de `oia-api`: `feat/ace-msgflow-emf`.
- [x] Externalizar los destinos de agentes a `agents.yaml`.
- [x] Mantener la lógica de instalación en Python y cargar desde configuración.
- [x] Documentar que agregar un agente futuro requiere modificar solo `agents.yaml`.
- [x] Implementar `python install_skills.py --doctor` como diagnóstico local del PC.
- [x] Documentar el procedimiento completo desde cero y los errores frecuentes.
- [x] Validar tipos, rutas y valores permitidos de `agents.yaml`.
- [x] Corregir la descripción del hash para no afirmar una verificación remota durante `--doctor`.
- [x] Ampliar la pipeline con `--doctor`, `--list-targets` y `install.cmd`.
- [x] Marcar la guía desde cero como procedimiento operativo principal y las
  secciones posteriores como referencia técnica.
- [x] Consolidar el README en un único manual con índice y eliminar secciones
  operativas duplicadas.

## Fase 1: Compatibilidad explícita

- [ ] Completar `agents.yaml` con versiones mínimas cuando cada agente las
  documente oficialmente.
- [ ] Clasificar cada agente como `supported`, `conditional` o `unsupported`.
- [ ] Mostrar en la salida si se verificaron archivos solamente o también la carga
  efectiva de la skill.
- [x] Actualizar la tabla de agentes del `README.md` con el nivel de soporte real.

## Fase 2: Diagnóstico

- [ ] Completar la detección de versiones para agentes que no exponen un
  ejecutable en el `PATH`.
- [x] Informar sistema operativo, Python, Git, agentes detectados, versiones,
  rutas, skills instaladas y compatibilidad.
- [x] Detectar si el agente requiere reinicio.
- [x] Generar un diagnóstico en formato humano y JSON.

## Fase 3: Versionado y seguridad

- [ ] Permitir instalación por commit o tag aprobado, además de rama.
- [ ] Registrar siempre repositorio, rama, commit y hash en el comprobante.
- [ ] Definir una lista de commits o versiones aprobadas para producción.
- [ ] Validar el contenido descargado antes de copiarlo a los destinos.

## Fase 4: Actualización segura

- [ ] Detectar archivos modificados localmente antes de `--update`.
- [ ] Mostrar los cambios antes de reemplazar una instalación existente.
- [ ] Mantener backups recuperables.
- [ ] Implementar `--rollback`.

## Fase 5: Pruebas

- [ ] Agregar pruebas para Windows, Linux, macOS y WSL.
- [ ] Probar rutas con espacios y caracteres especiales.
- [ ] Probar instalación simultánea en varios destinos.
- [ ] Probar permisos insuficientes y fallos durante la copia.
- [ ] Probar ramas inexistentes, skills incompletas y agentes no compatibles.
- [ ] Crear una prueba funcional por agente cuando exista un mecanismo oficial
  para confirmar la carga de `SKILL.md`.

## Fase 6: Experiencia de usuario

- [ ] Agregar modo interactivo para usuarios no técnicos.
- [ ] Mejorar mensajes de error con causa y acción recomendada.
- [ ] Separar los estados `INSTALLED`, `FILES-VERIFIED`, `LOAD-VERIFIED`,
  `RESTART-REQUIRED` y `UNSUPPORTED`.
- [ ] Mantener `--json` para pipelines y soporte técnico.

## Criterios de aceptación

- La documentación no promete integración universal.
- Cada agente informa claramente su nivel de soporte.
- El instalador diferencia integridad de archivos y carga efectiva.
- Se puede identificar exactamente el commit instalado.
- `python -m unittest discover -s tests -v` continúa pasando.
- Las pruebas multiplataforma se ejecutan en la pipeline sin modificar el HOME
  real de los desarrolladores.

## Orden recomendado

1. Implementar el manifiesto `agents.yaml`.
2. Implementar `--doctor`.
3. Añadir instalación por commit o tag.
4. Mejorar actualización y rollback.
5. Ampliar pruebas multiplataforma y funcionales.
6. Añadir modo interactivo y estados de salida más precisos.
