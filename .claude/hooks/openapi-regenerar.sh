#!/usr/bin/env bash
set -uo pipefail

FILE=$(python3 -c "import sys, json; print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))" <<< "$(cat)")

case "$FILE" in
  *app/models.py|*app/schemas.py|*app/main.py|*app/projects.py|*app/tasks.py) ;;
  *) exit 0 ;;
esac

if uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))" > openapi.json 2>/tmp/openapi-hook-error.log; then
  echo "openapi.json regenerado automaticamente tras editar $FILE."
else
  echo "AVISO: fallo la regeneracion automatica de openapi.json. Revisa /tmp/openapi-hook-error.log y regeneralo a mano (ver README.md)." >&2
fi

echo "AVISO: docs/esquema.md puede haber quedado desactualizado. Regeneralo con la skill describir-esquema."
