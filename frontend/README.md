# Docker Guide for the Application

---

## 1. Creating the Docker Image

### Prerequisites

* Docker Desktop installed and running.
* The project source code.

### Steps

1.  **Create an Environment File**

    In the project's root directory, create a `.env` file. This file provides the necessary build-time arguments for the Next.js application.

    ```env
    # .env
    NEXT_PUBLIC_LOGIN_API_URL=VALUE
    NEXT_PUBLIC_REGISTER_API_URL=VALUE
    NEXT_PUBLIC_RETRIEVAL_API_URL=VALUE
    NEXT_PUBLIC_UPDATE_FOLDERS_API_URL=VALUE
    NEXT_PUBLIC_SELECT_DATE_URL=VALUE
    NEXT_PUBLIC_GET_PPTS_URL=VALUE
    NEXT_PUBLIC_LIST_PDFS_API_URL=VALUE
    NEXT_PUBLIC_DOWNLOAD_PDF_API_URL=VALUE
    NEXT_PUBLIC_CHAT_API_URL=VALUE
    ```

2.  **Build the Image**

    Open a terminal in the project root (frontend) and run the command. Since your folder is named `frontend`, this will create an image named `frontend-web`.

    ```bash
    docker compose build
    ```

3.  **(Optional) Tag and Push to a Registry**

    To share the image, you must tag your local `frontend-web` image with a registry-friendly name and then push it.

    ```bash
    # Example for Docker Hub
    # 1. Tag your local image 'frontend-web' for the registry
    docker tag frontend-web:latest your-dockerhub-username/frontend:1.0

    # 2. Login to Docker Hub
    docker login

    # 3. Push the newly tagged image
    docker push your-dockerhub-username/frontend:1.0
    ```

---

## 2. Running the Application from a Shared Image

Follow these steps to run the application on any machine with Docker, using a pre-built image. You do not need the source code.

### Prerequisites

* Docker Desktop installed and running.

### Steps

1.  **Create an Environment File**

    Create a directory for your application deployment. Inside it, create a `.env` file with the runtime configuration values.

    ```env
    # .env
    # Use production or appropriate environment URLs here
    NEXT_PUBLIC_LOGIN_API_URL=VALUE
    # ...add all other required variables
    ```

2.  **Create a `docker-compose.yml` File**

    In the same directory, create a `docker-compose.yml` file. This file tells Docker how to run the shared image.

    **Important:** Replace `your-dockerhub-username/frontend:1.0` with the actual image you pushed to the registry.

    ```yaml
    # docker-compose.yml
    services:
      web:
        image: your-dockerhub-username/frontend:1.0 # <-- This matches the image you pushed
        container_name: nextjs-app
        ports:
          - "3000:3000"
        env_file:
          - ./.env
        restart: unless-stopped
    ```

3.  **Run the Application**

    Open a terminal in the directory containing the `.env` and `docker-compose.yml` files and run:

    ```bash
    docker compose up -d
    ```
    Docker will pull the image from the registry and start the container in the background.

4.  **Access the Application**

    You can now access the running application by navigating to **`http://localhost:3000`** in your web browser.

### Managing the Container

* **To see logs:** `docker logs nextjs-app`
* **To stop the application:** `docker compose down`