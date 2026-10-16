FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --uid 1000 --create-home --shell /bin/bash jovyan \
    && mkdir -p /home/jovyan/work /etc/jupyter /opt/course-materials \
    && chown -R 1000:1000 /home/jovyan

WORKDIR /home/jovyan
COPY apps/jupyter/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY apps/jupyter/jupyter_server_config.py /etc/jupyter/jupyter_server_config.py
COPY apps/jupyter/start-jupyter.sh /usr/local/bin/start-jupyter.sh
COPY --chown=1000:1000 learning/notebooks/ /opt/course-materials/
RUN chmod 0755 /usr/local/bin/start-jupyter.sh

USER 1000:1000
EXPOSE 8888
ENTRYPOINT ["/usr/local/bin/start-jupyter.sh"]
