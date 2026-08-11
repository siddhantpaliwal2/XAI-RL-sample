# syntax=docker/dockerfile:1
# Local base is built with Dockerfile.repo; Daytona uses an equivalent sealed snapshot.
FROM enterprise-backend-eng504-billing-base:v1

USER root
WORKDIR /app
RUN mkdir -p /logs/verifier
CMD ["/bin/bash"]
