FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY baggage_router ./baggage_router
RUN pip install --no-cache-dir .
ENTRYPOINT ["baggage-router"]
EXPOSE 8000
CMD ["serve", "--host", "0.0.0.0"]
