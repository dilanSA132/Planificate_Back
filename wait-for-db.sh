
echo "Esperando a que la base de datos esté lista..."

while ! nc -z db 5432; do
  sleep 2
done

echo "Base de datos lista. Iniciando FastAPI..."
exec "$@"
