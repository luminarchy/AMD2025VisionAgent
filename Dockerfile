FROM rocm/pytorch:latest
# Install basic development tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /open-webui/mcp
COPY mcp/server.py .
COPY mcp/tools.py .
COPY mcp/requirements.txt .

# Install additional dependencies
RUN pip3 install -r requirements.txt



