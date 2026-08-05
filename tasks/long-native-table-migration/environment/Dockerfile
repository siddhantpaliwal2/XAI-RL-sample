# syntax=docker/dockerfile:1
FROM bank-statement-parser-repo:v1

USER root
WORKDIR /app

# The base image contains the exact pre-migration source and its 135 PDF fixture
# corpus. Seal the history so the 62-commit oracle branch cannot be recovered.
RUN rm -rf .git \
 && git init -qb main \
 && git config user.email t@t \
 && git config user.name t \
 && git add -A \
 && git commit -qm "import codebase"

RUN mkdir -p /logs/verifier
WORKDIR /app
