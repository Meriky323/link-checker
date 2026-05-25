FROM python:3.11-slim

WORKDIR /app
COPY link_checker_app.py /app/link_checker_app.py
COPY browser_check.mjs /app/browser_check.mjs

ENV HOST=0.0.0.0
ENV PORT=8765
EXPOSE 8765

CMD ["python", "link_checker_app.py"]
