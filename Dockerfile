FROM rocm/pytorch:latest
# Install basic development tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /mcp
COPY mcp/server.py .
COPY mcp/tools.py .
COPY mcp/image.py .
COPY mcp/requirements.txt .
RUN mkdir /images

# Install additional dependencies
RUN pip3 install -r requirements.txt



