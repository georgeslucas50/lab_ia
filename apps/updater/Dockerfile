FROM docker:29.8-cli

RUN apk add --no-cache git python3

WORKDIR /opt/updater
COPY server.py worker.py git-askpass /opt/updater/
RUN chmod 0755 /opt/updater/git-askpass

EXPOSE 8091
CMD ["python3", "/opt/updater/server.py"]
