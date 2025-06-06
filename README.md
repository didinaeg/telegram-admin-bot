# Bot Administrador de Telegram

Un bot de Telegram multifuncional diseñado para la gestión y administración de grupos de chat con características avanzadas de moderación, descarga de contenido multimedia y funcionalidades administrativas.

## Características Principales

### Moderación y Administración
- **Comandos de moderación**: Ban, unban y unrestrict de usuarios
- **Control de acceso**: Sistema de permisos restringido a administradores
- **Filtro de contenido**: Detección automática de palabras prohibidas
- **Filtro de enlaces**: Control automático de enlaces de Telegram, TikTok y sitios maliciosos
- **Gestión de nuevos miembros**: Saludo automático con mensaje de bienvenida y reglas

### Descarga de Contenido Multimedia
- **YouTube**: Descarga de videos con interfaz interactiva y control de progreso
- **Instagram**: Descarga automática de posts, reels e imágenes
- **Gestión de descargas**: Sistema de cancelación y control de descargas activas por usuario

### Funcionalidades Automatizadas
- **Mensajes automáticos**: Sistema de envío programado de mensajes
- **Limpieza automática**: Eliminación automática de mensajes después de un tiempo determinado
- **Monitoreo en tiempo real**: Sistema de alertas para administradores

### Utilidades Adicionales
- **Decodificador Base64**: Funcionalidad inline y por comandos
- **Información del chat**: Comando para obtener ID del chat
- **Consultas inline**: Soporte para interacciones inline del bot

## Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- Token de bot de Telegram (obtenido de [@BotFather](https://t.me/BotFather))
- MongoDB (opcional, para funcionalidades de base de datos)

### Instalación Local

1. **Clonar el repositorio**:
```bash
git clone https://github.com/didinaeg/telegram-admin-bot.git
cd telegram-admin-bot
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**:
Crear un archivo `.env` en la raíz del proyecto:
```env
TELEGRAM_BOT_TOKEN="tu_token_aqui"
MONGODB_URI="tu_uri_mongodb_aqui"  # Opcional
```

4. **Ejecutar el bot**:
```bash
python main.py
```

### Instalación con Docker

1. **Construir y ejecutar con Docker Compose**:
```bash
docker-compose up -d
```

## Comandos Disponibles

### Comandos Generales
- `/start` - Iniciar conversación con el bot
- `/rules` - Mostrar las reglas del grupo
- `/chatid` - Obtener el ID del chat actual

### Comandos de Administración (Solo Admins)
- `/ban` - Banear usuario (responder a mensaje)
- `/unban` - Desbanear usuario (responder a mensaje)
- `/unrestrict` - Quitar restricciones a usuario (responder a mensaje)
- `/auto` - Iniciar mensajes automáticos
- `/stop` - Detener mensajes automáticos
- `/decode [base64]` - Decodificar texto en base64

### Funcionalidades Automáticas
- **Descarga de YouTube**: Enviar enlace de YouTube para activar interfaz de descarga
- **Descarga de Instagram**: Enviar enlace de Instagram para descarga automática
- **Consultas Inline**: Usar `@nombre_bot [base64]` para decodificar inline

## Estructura del Proyecto

```
admin_bot/
├── main.py                 # Archivo principal del bot
├── admin.py                # Funciones de administración
├── instagram.py            # Descarga de contenido de Instagram
├── utils.py                # Utilidades y decoradores
├── messages.py             # Mensajes predefinidos y reglas
├── estados.py              # Estados para conversaciones
├── conversations/          # Módulos de conversación
│   └── video_download.py   # Lógica de descarga de videos
├── requirements.txt        # Dependencias Python
├── Dockerfile             # Configuración Docker
├── docker-compose.yml     # Orquestación Docker
└── .env                   # Variables de entorno (no incluido en git)
```

## Seguridad y Permisos

### Sistema de Administradores
El bot utiliza un sistema de lista blanca de administradores definido en `utils.py`:
```python
LIST_OF_ADMINS = [123456789]  # IDs de Telegram de administradores
```

### Palabras Prohibidas
El sistema detecta automáticamente palabras prohibidas y notifica a los administradores:
- Sistema de alertas en tiempo real
- Envío de notificaciones al chat de administradores
- Enlaces al mensaje original para revisión

### Filtros de Enlaces
- **Telegram**: Restricción temporal (7 días) para usuarios no admin
- **TikTok**: Bloqueo de enlaces
- **Sitios maliciosos**: Ban automático para enlaces peligrosos

## Tecnologías Utilizadas

- **[python-telegram-bot](https://python-telegram-bot.org/)** - Framework principal para Telegram
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Descarga de videos de YouTube
- **[instaloader](https://instaloader.github.io/)** - Descarga de contenido de Instagram
- **[pymongo](https://pymongo.readthedocs.io/)** - Cliente MongoDB para Python
- **[python-dotenv](https://saurabh-kumar.com/python-dotenv/)** - Gestión de variables de entorno

## Características Técnicas

### Persistencia de Datos
- Utiliza `PicklePersistence` para mantener estado entre reinicios
- Soporte para MongoDB para almacenamiento avanzado

### Gestión de Descargas
- Sistema de cancelación de descargas activas
- Control de progreso en tiempo real
- Manejo de múltiples usuarios simultáneos

### Servidor HTTP Integrado
- Servidor HTTP en puerto 8080 para health checks
- Diseñado para despliegues en contenedores

## Despliegue en Producción

### Variables de Entorno Requeridas
```env
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
MONGODB_URI=mongodb://localhost:27017/bot_db  # Opcional
```

### Docker
```bash
# Construir imagen
docker build -t telegram-admin-bot .

# Ejecutar contenedor
docker run -d --env-file .env -p 8080:8080 telegram-admin-bot
```

## Ejemplos de Uso

### Moderación de Grupo
1. Responder a un mensaje problemático con `/ban`
2. El bot baneará automáticamente al usuario
3. Los administradores recibirán notificación

### Descarga de Videos
1. Enviar enlace de YouTube al grupo
2. Hacer clic en "Iniciar descarga"
3. Monitorear progreso en tiempo real
4. Recibir video descargado

### Configuración de Mensajes Automáticos
1. Usar `/auto` para iniciar
2. El bot enviará mensajes cada 13 horas
3. Usar `/stop` para detener

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crear una branch para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la branch (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

