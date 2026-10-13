# Frontend

The Docker setup targets a React application using Vite and npm for local development.
The React application has not been created yet. Before building, add its source,
`package.json` with a `dev` script that runs `vite`, and preferably `package-lock.json`
to this directory. The image uses `npm ci` when a lockfile exists, otherwise `npm install`.

From the project root, run:

```sh
docker compose up --build frontend
```

This also starts the backend dependency, which needs its own runnable FastAPI app.
To run only the frontend:

```sh
docker compose up --build --no-deps frontend
```

Open http://localhost:5173. Source files are mounted for live editing; container
dependencies are stored separately in the `frontend_node_modules` volume.
After changing dependencies, update the named dependency volume with
`docker compose run --rm --no-deps frontend npm install`, then restart the frontend.
Rebuild the image as well to keep it up to date.

For browser API calls, use http://localhost:8000 or configure a Vite proxy to
http://backend:8000. Direct browser calls require the backend to allow the frontend
origin through CORS. Only variables prefixed with `VITE_` are exposed by Vite to
browser code; never use that prefix for secrets.

This Dockerfile runs the development server. A production deployment will need
a separate build and static-file serving setup.
