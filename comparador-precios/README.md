# Comparador de Precios MVP

Este proyecto es un Minimum Viable Product (MVP) de una plataforma comparadora de precios de productos, inspirada en sitios como Kayak. Permite a los usuarios buscar productos y ver una lista comparativa de precios obtenidos mediante web scraping de sitios predefinidos.

## Tabla de Contenidos

- [Tech Stack](#tech-stack)
- [Características (MVP)](#características-mvp)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Configuración del Entorno Local](#configuración-del-entorno-local)
  - [Prerrequisitos](#prerrequisitos)
  - [Variables de Entorno](#variables-de-entorno)
  - [Instalación](#instalación)
- [Ejecución (Desarrollo Local)](#ejecución-desarrollo-local)
- [Despliegue (GCP con Terraform y Docker Compose)](#despliegue-gcp-con-terraform-y-docker-compose)
  - [Prerrequisitos de Despliegue](#prerrequisitos-de-despliegue)
  - [Pasos de Despliegue](#pasos-de-despliegue)
- [Web Scraping](#web-scraping)
- [Próximos Pasos y Mejoras Futuras](#próximos-pasos-y-mejoras-futuras)

## Tech Stack

- **Frontend:** React (Vite), Zustand (State Management), Axios (HTTP Client), CSS Modules/Plain CSS
- **Backend:** Python, FastAPI (Web Framework), SQLAlchemy (ORM), Pydantic (Data Validation)
- **Base de Datos Principal:** PostgreSQL
- **Base de Datos de Caché:** Redis
- **Web Scraping:** Python (httpx, BeautifulSoup4)
- **Contenerización:** Docker, Docker Compose
- **Infraestructura como Código (IaC):** Terraform
- **Plataforma Cloud:** Google Cloud Platform (GCP) - Google Compute Engine (GCE)
- **Servidor Web (Producción):** Nginx (sirviendo frontend estático y como proxy inverso para el backend)

## Características (MVP)

- Búsqueda de productos por término clave.
- Obtención de precios mediante web scraping de fuentes predefinidas (MercadoLibre Chile, Falabella Chile).
- Visualización de resultados comparativos: nombre del producto en la fuente, precio, nombre de la fuente, enlace directo al producto.
- Caché de resultados de búsqueda (Redis) para mejorar rendimiento y reducir scraping.
- Ejecución de tareas de scraping en segundo plano (FastAPI BackgroundTasks) para no bloquear la respuesta de la API.
- Entorno de desarrollo y producción contenerizado con Docker y Docker Compose.
- Infraestructura básica en GCP (VM GCE) gestionada con Terraform.

## Estructura del Proyecto

```
comparador-precios/
├── backend/              # Código del backend (FastAPI)
│   ├── app/              # Lógica principal de la aplicación
│   │   ├── api/          # Endpoints y routers API
│   │   ├── core/         # Configuración, clientes (Redis)
│   │   ├── crud/         # Operaciones CRUD para la base de datos
│   │   ├── db/           # Configuración de sesión y base de SQLAlchemy
│   │   ├── models/       # Modelos Pydantic y SQLAlchemy
│   │   ├── scrapers/     # Módulos de scraping por sitio
│   │   ├── services/     # Lógica de negocio (ej: SearchService)
│   │   └── main.py       # Punto de entrada de FastAPI
│   ├── tests/            # (Pendiente) Pruebas unitarias/integración
│   ├── Dockerfile        # Dockerfile para el backend
│   ├── requirements.txt  # Dependencias Python
│   ├── .env              # Variables de entorno locales (¡NO SUBIR A GIT!)
│   └── .env.example      # Ejemplo de variables de entorno locales
│   └── .env.prod.example # Ejemplo de variables de entorno de producción
├── frontend/             # Código del frontend (React)
│   ├── public/           # Archivos estáticos públicos
│   ├── src/              # Código fuente de React
│   │   ├── components/   # Componentes reutilizables (SearchBar, ResultCard, etc.)
│   │   ├── services/     # Cliente API (apiClient.js)
│   │   ├── store/        # Estado global (Zustand - searchStore.js)
│   │   └── ...           # Otros archivos (App.jsx, main.jsx, CSS)
│   ├── Dockerfile        # Dockerfile multi-stage para frontend (build + Nginx)
│   ├── nginx.conf        # Configuración de Nginx para producción
│   ├── package.json      # Dependencias y scripts de Node.js
│   └── vite.config.js    # Configuración de Vite
├── infra/                # Configuración de infraestructura
│   ├── terraform/        # Archivos Terraform para GCP
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── scripts/          # Scripts auxiliares (ej: startup script para VM)
│       └── startup-script.sh
├── docker-compose.yml      # Docker Compose para desarrollo local
├── docker-compose.prod.yml # Docker Compose para producción
├── init-db.sql           # Script SQL inicial para crear tablas (usado en dev)
└── README.md             # Este archivo
```

## Configuración del Entorno Local

### Prerrequisitos

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (usualmente incluido con Docker Desktop)
- [Node.js](https://nodejs.org/) (v18+ recomendado, aunque v16 podría funcionar con warnings) y npm

### Variables de Entorno

1.  **Backend:** Copia `backend/.env.example` a `backend/.env`. Los valores por defecto deberían funcionar para el desarrollo local con Docker Compose.
    ```bash
    cp backend/.env.example backend/.env
    ```
2.  **Frontend:** No se requiere un `.env` para la configuración básica local, ya que `VITE_API_BASE_URL` se configura en `docker-compose.yml` para el entorno de desarrollo (o se usa el relativo para Nginx en producción).

### Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone <url-del-repositorio>
    cd comparador-precios
    ```
2.  **Crea el archivo `.env` del backend** (como se indicó arriba).
3.  **Instala dependencias del frontend** (necesario para que el volumen funcione correctamente con `node_modules`):
    ```bash
    cd frontend
    npm install
    cd ..
    ```
    *(Nota: Las dependencias del backend se instalan dentro del contenedor Docker).*

## Ejecución (Desarrollo Local)

1.  **Asegúrate que Docker esté corriendo.**
2.  **Desde la raíz del proyecto (`comparador-precios/`), ejecuta:**
    ```bash
    docker-compose up --build
    ```
    La primera vez, esto construirá las imágenes de Docker para el backend y frontend, y luego iniciará todos los contenedores (backend, frontend-dev, db, cache). La base de datos se inicializará con las tablas definidas en `init-db.sql`.
3.  **Accede a la aplicación:**
    -   Frontend (React App con Hot Reload): [http://localhost:5173](http://localhost:5173)
    -   Backend API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
    -   Backend API Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)
4.  **Para detener los contenedores:** Presiona `Ctrl+C` en la terminal donde corre `docker-compose up`, o abre otra terminal en el mismo directorio y ejecuta:
    ```bash
    docker-compose down
    ```

## Despliegue (GCP con Terraform y Docker Compose)

Esta sección describe cómo desplegar la aplicación en una VM de Google Compute Engine usando Terraform para la infraestructura y Docker Compose para correr la aplicación en producción.

### Prerrequisitos de Despliegue

- [Terraform CLI](https://learn.hashicorp.com/tutorials/terraform/install-cli) instalado.
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) instalado y configurado (autenticado con `gcloud auth login` y `gcloud config set project YOUR_PROJECT_ID`).
- Un proyecto GCP creado.
- Un par de claves SSH (pública y privada). La clave pública se proporcionará a Terraform.
- Permisos necesarios en GCP para crear recursos (Compute Engine, Firewall, etc.).

### Pasos de Despliegue

1.  **Configurar Variables de Terraform:**
    -   Navega a `infra/terraform/`.
    -   Crea un archivo `terraform.tfvars` (este archivo no debe subirse a Git) o exporta las variables de entorno requeridas:
        ```terraform
        # terraform.tfvars
        gcp_project_id = "tu-proyecto-gcp"
        ssh_user       = "tu-usuario-ssh" # ej: devops
        ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAA..." # Contenido de tu archivo .pub
        ```
        O usando variables de entorno:
        ```bash
        export TF_VAR_gcp_project_id="tu-proyecto-gcp"
        export TF_VAR_ssh_user="tu-usuario-ssh"
        export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_rsa.pub)" # Ejemplo
        ```
2.  **Inicializar Terraform:**
    ```bash
    cd infra/terraform
    terraform init
    ```
3.  **Planificar y Aplicar Cambios:**
    ```bash
    terraform plan -out=tfplan # Revisa los recursos que se crearán
    terraform apply tfplan     # Crea la infraestructura en GCP
    ```
    Toma nota de la IP externa (`vm_instance_external_ip`) y el comando SSH (`ssh_command`) que Terraform mostrará como salida.
4.  **Configurar Entorno de Producción:**
    -   Crea el archivo `.env.prod` en `backend/` basado en `backend/.env.prod.example`. **Asegúrate de usar contraseñas seguras y configurar `BACKEND_CORS_ORIGINS` si es necesario.**
    -   Sube este archivo `.env.prod` de forma segura a la VM (usando `scp` o pegando el contenido vía SSH). Guárdalo en la ruta esperada por `docker-compose.prod.yml` (ej: `~/comparador-precios/backend/.env.prod`).
5.  **Desplegar la Aplicación en la VM:**
    -   Conéctate a la VM usando el comando SSH de la salida de Terraform:
        ```bash
        ssh tu-usuario-ssh@VM_EXTERNAL_IP
        ```
    -   Clona el repositorio del proyecto en la VM:
        ```bash
        git clone <url-del-repositorio>
        cd comparador-precios
        ```
    -   Copia el archivo `.env.prod` que subiste al directorio `backend/`.
    -   Ejecuta Docker Compose en modo producción:
        ```bash
        # Asegúrate que el usuario actual esté en el grupo 'docker' (el startup script lo intenta)
        # Podrías necesitar re-loguearte o usar 'newgrp docker'
        docker compose -f docker-compose.prod.yml pull # Opcional: Obtener imágenes base más recientes
        docker compose -f docker-compose.prod.yml up -d --build # Construye y levanta en segundo plano
        ```
6.  **Verificar:**
    -   Revisa que los contenedores estén corriendo: `docker ps`
    -   Revisa los logs: `docker compose -f docker-compose.prod.yml logs -f`
    -   Accede a la aplicación usando la IP externa de la VM en tu navegador: `http://VM_EXTERNAL_IP`

## Web Scraping

- Los scrapers se encuentran en `backend/app/scrapers/`.
- `base_scraper.py` define la clase base abstracta.
- Scrapers específicos (ej: `mercadolibre_scraper.py`) heredan de la base e implementan la lógica de construcción de URL y parseo de HTML para cada sitio.
- **Importante:** Los selectores CSS/HTML usados para extraer datos son frágiles y pueden romperse si el sitio web fuente cambia su estructura. Se requiere mantenimiento periódico.
- Considera aspectos legales y éticos del web scraping (revisar `robots.txt`, términos de servicio, evitar sobrecargar los servidores).

## Próximos Pasos y Mejoras Futuras

- **Añadir más fuentes de scraping:** Implementar scrapers para otros sitios (ej: Paris.cl).
- **Mejorar Resiliencia de Scrapers:** Usar técnicas más robustas (XPath, JSON-LD si está disponible, análisis de estructura) o explorar librerías/servicios anti-scraping (con precaución).
- **Planificación de IA/ML:** Integrar modelos para extracción de datos más inteligente y adaptable (ver Fase 7 de la guía original).
- **Filtros Avanzados:** Añadir más filtros en el frontend (por marca, características, vendedor).
- **Interfaz de Usuario:** Mejorar el diseño, añadir paginación, feedback de carga más detallado.
- **Pruebas:** Implementar pruebas unitarias (backend/frontend), de integración (API) y E2E.
- **Monitoreo y Logging:** Configurar logging centralizado y monitoreo básico (ej: GCP Monitoring, Prometheus/Grafana).
- **Seguridad:** Configurar HTTPS (ej: con Let's Encrypt y Certbot en Nginx), restringir acceso SSH, gestionar secretos de forma segura (ej: GCP Secret Manager).
- **Escalabilidad:** Considerar balanceadores de carga, escalar VMs o pasar a servicios gestionados (Cloud Run, GKE) si el tráfico aumenta.
- **Migraciones de Base de Datos:** Usar una herramienta como Alembic para gestionar cambios en el esquema de la base de datos.
- **Tareas Asíncronas Robustas:** Considerar Celery con Redis/RabbitMQ como broker para tareas de scraping más complejas o programadas.
