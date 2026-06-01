FROM python:3.11-slim
COPY entrypoint.sh /entrypoint.sh
COPY scanner.py /scanner.py
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
