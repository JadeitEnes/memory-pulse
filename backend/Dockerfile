FROM python:3.11-slim as base

RUN groupadd -r appuser && useradd -r -m -g appuser appuser

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CMDSTAN=/home/appuser/.cmdstan

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
RUN  pip install --upgrade pip && \
     pip install -r requirements/base.txt

RUN mkdir -p /home/appuser/.cmdstan && chown -R appuser:appuser /home/appuser
USER appuser
WORKDIR /home/appuser
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan(dir='/home/appuser/.cmdstan', cores=4)"
WORKDIR /app
USER root
ENV CMDSTAN=""
RUN rm -rf /usr/local/lib/python3.11/site-packages/prophet/stan_model/cmdstan-*


FROM base as development

COPY requirements/dev.txt requirements/dev.txt
RUN pip install -r requirements/dev.txt

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base as production

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]