# TODO: Choose a base image appropriate for your task
FROM python:3.11-slim
WORKDIR /app

# TODO: Install system dependencies (always keep procps)
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# TODO: Install Python dependencies (pin versions for reproducibility)
# RUN pip install numpy==1.24.0 pandas==2.0.0

# TODO: COPY input data into the container
# IMPORTANT: Every COPY source file/dir must exist under environment/
# COPY data/ /app/data/

# TODO: Generate challenge data (optional, pick ONE approach)
#
# Approach A — Setup script (recommended for complex data):
#   COPY setup.sh /tmp/setup.sh
#   RUN bash /tmp/setup.sh && rm /tmp/setup.sh
#
# Approach B — Inline commands (for simple files):
#   RUN printf 'line1\nline2\nline3\n' > /app/config.txt
#   RUN python3 -c "import json; json.dump({'key': 'value'}, open('/app/config.json','w'))"
#
# FORBIDDEN — Heredoc syntax (causes Docker build failure):
#   RUN cat > /file << 'EOF'
#   content
#   EOF
