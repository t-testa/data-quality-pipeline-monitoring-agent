FROM python:3.12-slim-trixie@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends curl ca-certificates unixodbc \
    && curl -fsSLo /tmp/packages-microsoft-prod.deb https://packages.microsoft.com/config/debian/13/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 libgssapi-krb5-2 \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/* /tmp/packages-microsoft-prod.deb
COPY requirements-toolchain.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-toolchain.lock
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
# Package installers and their vendored libraries are not needed by the runtime.
RUN pip uninstall -y pip && rm -rf /usr/local/lib/python3.12/ensurepip
RUN useradd --uid 10001 --create-home monitor && mkdir /data && chown monitor:monitor /data
# No runtime feature needs setuid/setgid helpers. This is a compensating control,
# not a claim that the underlying distribution advisories are fixed.
RUN find /usr -xdev -type f -perm /6000 -exec chmod a-s {} +
COPY dqagent ./dqagent
USER 10001:10001
ENV DQ_DATA_DIR=/data
EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/ready',timeout=2)"
CMD ["python", "-m", "uvicorn", "dqagent.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8765", "--workers", "1", "--no-access-log", "--limit-concurrency", "20", "--timeout-keep-alive", "5"]
