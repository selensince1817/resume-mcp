# Dockerfile

# ---- STAGE 1: Builder ----
# Use a full Python image to build our dependencies. We name it 'builder'.
FROM python:3.11 as builder

# Install uv, our Python package manager
RUN pip install uv

# Set the working directory inside the container
WORKDIR /app

# Create a virtual environment within the builder
RUN uv venv

# Copy only the dependency definition files first
# This leverages Docker's layer caching. This step only reruns if these files change.
COPY pyproject.toml uv.lock README.md ./

# Install all dependencies into the .venv using the lockfile for a reproducible build
# The activate command ensures uv installs into our venv
RUN . .venv/bin/activate && uv sync --no-cache --frozen



# ---- STAGE 2: Runner ----
# Use a slim Python image for the final, lightweight container
FROM python:3.11-slim as runner

# Set the working directory
WORKDIR /app

# Copy the virtual environment with all its installed dependencies from the builder stage
COPY --from=builder /app/.venv .venv

# Copy your application's source code into the container
COPY src/ ./src

# Set the PYTHONPATH environment variable
# This tells Python to look for packages inside the /app/src directory,
# which is necessary for the `src` layout to work correctly.
ENV PYTHONPATH=/app/src

# Command to run your MCP server
# We execute the python binary from our virtual environment
#CMD ["./.venv/bin/python", "-m", "resume_mcp.mcp_server.server"]
CMD [".venv/bin/overleaf-cli", "read", "CV-XeLate", "main.tex"]

