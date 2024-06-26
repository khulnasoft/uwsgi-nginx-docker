import os
import time

import docker
import requests
from docker.models.containers import Container

from ..utils import (
    CONTAINER_NAME,
    get_logs,
    get_nginx_config,
    get_response_text1,
    remove_previous_container,
)

client = docker.from_env()


def verify_container(container: Container, response_text: str) -> None:
    response = requests.get("http://127.0.0.1:8000")
    assert response.text == response_text
    nginx_config = get_nginx_config(container)
    assert "client_max_body_size 1m;" in nginx_config
    assert "worker_processes 2;" in nginx_config
    assert "listen 80;" in nginx_config
    assert "worker_connections 2048;" in nginx_config
    assert "worker_rlimit_nofile 2048;" in nginx_config
    assert "daemon off;" in nginx_config
    assert "listen 80;" in nginx_config
    assert "include uwsgi_params;" in nginx_config
    assert "uwsgi_pass unix:///tmp/uwsgi.sock;" in nginx_config
    logs = get_logs(container)
    assert "getting INI configuration from /app/uwsgi.ini" in logs
    assert "getting INI configuration from /etc/uwsgi/uwsgi.ini" in logs
    assert "ini = /app/uwsgi.ini" in logs
    assert "ini = /etc/uwsgi/uwsgi.ini" in logs
    assert "socket = /tmp/uwsgi.sock" in logs
    assert "chown-socket = nginx:nginx" in logs
    assert "chmod-socket = 664" in logs
    assert "hook-master-start = unix_signal:15 gracefully_kill_them_all" in logs
    assert "need-app = true" in logs
    assert "die-on-term = true" in logs
    assert "show-config = true" in logs
    assert "wsgi-file = /app/main.py" in logs
    assert "processes = 8" in logs
    assert "cheaper = 3" in logs
    assert "Checking for script in /app/prestart.sh" in logs
    assert "Running script /app/prestart.sh" in logs
    assert (
        "Running inside /app/prestart.sh, you could add migrations to this file" in logs
    )
    assert "spawned uWSGI master process" in logs
    assert "spawned uWSGI worker 1" in logs
    assert "spawned uWSGI worker 2" in logs
    assert "spawned uWSGI worker 3" in logs
    assert "spawned uWSGI worker 4" not in logs
    assert 'running "unix_signal:15 gracefully_kill_them_all" (master-start)' in logs
    assert "success: nginx entered RUNNING state, process has stayed up for" in logs
    assert "success: uwsgi entered RUNNING state, process has stayed up for" in logs


def test_env_vars_1() -> None:
    name = os.getenv("NAME")
    image = f"khulnasoft/uwsgi-nginx:{name}"
    response_text = get_response_text1()
    sleep_time = int(os.getenv("SLEEP_TIME", 3))
    remove_previous_container(client)
    container = client.containers.run(
        image,
        name=CONTAINER_NAME,
        environment={
            "UWSGI_CHEAPER": 3,
            "UWSGI_PROCESSES": 8,
            "NGINX_MAX_UPLOAD": "1m",
            "NGINX_WORKER_PROCESSES": 2,
            "NGINX_WORKER_CONNECTIONS": 2048,
            "NGINX_WORKER_OPEN_FILES": 2048,
        },
        ports={"80": "8000"},
        detach=True,
    )
    time.sleep(sleep_time)
    verify_container(container, response_text)
    container.stop()
    # Test that everything works after restarting too
    container.start()
    time.sleep(sleep_time)
    verify_container(container, response_text)
    container.stop()
    container.remove()
