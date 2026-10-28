# Contenido

`content/` es la fuente única del perfil. Todo lo demás se genera a partir de aquí:

| Artefacto | Qué es |
|---|---|
| `profile.json` | Datos que consume el portfolio (`abrah.dev`) |
| `CV_Abraham_Escalona.md` | CV generado |
| `CV_Abraham_Escalona.pdf` | CV imprimible |
| `README.md` | Perfil de GitHub |

**No edites esos cuatro ficheros a mano**: se sobrescriben.

## Estructura

```text
content/
├── profile.md        # identidad, enlaces y textos por destino
├── skills.yml        # grupos de skills
├── experience/       # type: job
├── projects/         # type: project
├── education/        # type: education
└── awards/           # type: award
```

Un fichero por entrada. El nombre del fichero es el slug (`karter.md` → `karter`).

## Comandos

Requisitos: Python 3 con PyYAML. Para el PDF, `pandoc` y `weasyprint`.

```sh
pnpm validate      # valida content/ y sale con error si algo no cuadra
pnpm build:profile # profile.json + CV.md + README.md
pnpm cv:pdf        # CV.md -> CV.pdf
pnpm build         # validate + build:profile + cv:pdf
```

En CI lo hace `.github/workflows/pipeline.yml` en cada push a `main` que toque `content/`, `scripts/`, el CSS o el README, y commitea los artefactos.

## Cómo añadir una entrada

Crea el `.md` en la carpeta que corresponda, con frontmatter y cuerpo:

```markdown
---
type: project
title: Nombre del proyecto
summary: Una frase para la tarjeta del portfolio.
start: 2026-01
current: true
repo: https://github.com/abrahdev/ejemplo
demo: https://ejemplo.dev
image: ejemplo.png
tags: [Astro, TailwindCSS]
---

- Primer punto.
- Segundo punto.
```

El cuerpo son los bullets que salen en el CV y en la ficha del portfolio.

## Campos

| Campo | Tipo | Uso |
|---|---|---|
| `type` | `job` `project` `education` `award` | Se infiere de la carpeta; si lo pones, debe coincidir |
| `title` | texto | Obligatorio |
| `org` | texto | Obligatorio en `job` y `education` |
| `start` | `YYYY` o `YYYY-MM` | Obligatorio |
| `end` | igual que `start` | Opcional |
| `current` | booleano | `true` = «Actual» / «Actualidad» |
| `summary` | texto | Resumen corto para la tarjeta del portfolio |
| `card_title` | texto | Título corto de tarjeta si `title` es largo (CV) |
| `role` | texto | Puesto, solo proyectos (ej. «Desarrollador Principal») |
| `link` | URL | Enlace genérico |
| `repo` / `demo` | URL | Solo proyectos |
| `image` | texto | Nombre del fichero en `abrah.dev/src/assets/projects/` |
| `tags` | lista | Deben existir en `skills.yml` |
| `cv` | booleano | `false` para excluir del CV (por defecto `true`) |
| `portfolio` | booleano | `false` para excluir del portfolio (por defecto `true`) |
| `draft` | booleano | `true` lo excluye de todo |
| `cv_group` | texto | Agrupa varias entradas en un solo bloque del CV |
| `cv_group_summary` | markdown | Sustituye la concatenación de cuerpos en ese bloque del CV |

### Fechas

- `start: 2025` → «2025».
- `start: 2025-06` → «Junio 2025».
- `current: true` → «Junio 2025 - Actualidad».
- `end` igual que `start` → fecha única.
- Sin `end` ni `current` → fecha única.

El orden es por `start` descendente.

### Grupos del CV

El Home Lab son cuatro entradas independientes en el portfolio, pero en el CV salen como un bloque:

```yaml
cv_group: Administrador de Home Lab & IoT
cv_group_summary: |
  - Un bullet.
  - Otro bullet.
```

Solo `cv_group_summary` afecta al CV; `profile.json` y el portfolio no cambian.

## `profile.md`

- **Frontmatter**: nombre, email, teléfono, avatar y enlaces.
  - `phone` va solo al CV; nunca se publica en `profile.json`.
  - `links.linkedin` usa `https://info.abrah.dev`.
  - `avatar` es una ruta relativa al repo (`assets/me.jpg`).
- **`## CV`**: texto de OBJETIVO.
- **`## Portfolio`**: texto del hero.
- **`## README`**: párrafos del «About me» del README.
- **`## Soft skills`**: bullets `- **Título:** texto`.

Si falta `## Portfolio`, se usa `## CV`.

## `skills.yml`

```yaml
groups:
  - id: infra
    label: DevOps & Infra
    items:
      - { name: Docker, icon: docker, skillicon: docker }
      - { name: Proxmox, skillicon: "https://go-skill-icons.vercel.app/api/icons?i=proxmox" }
      - VPN
```

- Forma corta (`- VPN`) o larga (`{ name: ..., icon: ..., skillicon: ... }`).
- `icon`: clave del catálogo SVG de `abrah.dev`.
- `skillicon`: slug de `skillicons.dev`, URL completa (si el icono no está en skillicons) o ruta a un `.svg` local.
- Las URLs con `?` **deben ir entrecomilladas** en YAML.
- Los `tags` de las entradas deben coincidir exactamente con un `name`.

## Assets

- `assets/me.jpg`: foto del CV.
- `assets/avatar.png`: avatar de perfil.

Si cambias la foto del CV, actualiza `avatar` en `content/profile.md`.

## Validación

`pnpm validate` comprueba:

- Frontmatter parseable y claves conocidas.
- `type` coherente con la carpeta.
- Fechas válidas y `end` no anterior a `start`.
- `org` en trabajos y educación.
- URLs `http(s)`.
- Tags existentes en `skills.yml`.
- Skills duplicadas o sin nombre.
- `skillicon` con formato válido.

Si algo falla, el CI no genera nada ni commitea.
