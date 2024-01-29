<a href="https://qwestar.ai/"><img src="https://qwestar.ai/wp-content/uploads/2024/01/qwestar1-e1706288179108.png" alt="Qwestart"></a>

Qwestar AI es una plataforma que permite a los usuarios crear sus propios juegos RPG.

## Configuración

### Variables de entorno

Para ejecutar el proyecto, es necesario configurar las siguientes variables de entorno en un archivo `./envs/.env`:

- `authjwt_secret_key`: Clave secreta utilizada para firmar los tokens JWT.
- `host_database`: Dirección del host de tu base de datos.
- `port_database`: Puerto en el que se ejecuta tu base de datos.
- `OPENAI_API_KEY`: Clave de API para OpenAI.
- `OPENAI_API_ORG_ID`: ID de organización para OpenAI.
- `admin_superuser`: Nombre de usuario del superusuario administrador.
- `admin_superuser_password`: Contraseña del superusuario administrador.
- `DATABASE_URI`: URI de conexión a tu base de datos.

Ademas se debe crear un archivo `./envs/.env_postgrees` con las siguientes variables de entorno:

- `POSTGRES_USER`: Nombre de usuario de tu base de datos.
- `POSTGRES_PASSWORD`: Contraseña de tu base de datos.
- `POSTGRES_DB`: Nombre de tu base de datos.

Por seguridad, la carpeta `./envs/` se encuentra en el archivo `.gitignore` y no se subirá al repositorio.

### Ejecución

Para ejecutar el proyecto, es necesario tener instalado [Docker](https://docs.docker.com/get-docker/)
y [Docker Compose](https://docs.docker.com/compose/install/). Una vez instalados, se debe ejecutar el siguiente comando
usando Make:

Para construir las imágenes de Docker, se debe ejecutar el siguiente comando usando Make:

```bash
make build
```

Para iniciar la ejecución del proyecto, se debe ejecutar el siguiente comando usando Make:

```bash
make up
```

Para realizar la migración de la base de datos, se debe ejecutar el siguiente comando usando Make:

```bash
make migrate
```

Para aplicar los cambios en la base de datos, se debe ejecutar el siguiente comando usando Make:

```bash 
make apply-migrations
```

Para para la ejecución del proyecto, se debe ejecutar el siguiente comando usando Make:

```bash
make stop 
```

# Servicios

Para acceder a los servicios, se debe ingresar a la siguiente URL:

```bash
http://localhost/v1/api/docs
```

# Documentación

Para acceder a la documentación, se debe ingresar a la siguiente URL:

```bash
http://localhost/v1/api/redocs
```

<div style="display: flex; justify-content: space-around;">
  <a href="https://fastapi.tiangolo.com"><img width="200px" src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="FastAPI"></a>
</div>