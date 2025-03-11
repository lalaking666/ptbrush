#! /bin/bash
set -e
if [ "$1" = 'start' ]; then
    USER=app
    # 修改app用户的UID和GID
    usermod -o -u ${PUID} ${USER}
    groupmod -o -g ${PGID} ${USER} >/dev/null 2>&1 || :
    usermod -g ${PGID} ${USER}

    # 将挂载的目录都修改一下权限
    # 处理data目录
    if [ ! -d "/app/data" ]; then
        echo ""
    else
        mkdir -p /app/data
        chown -R ${PUID}:${PGID} /app/data
    fi

    # 处理源码目录
     chown -R ${PUID}:${PGID} /app
    echo "Starting..."
    cd /app
    gosu ${USER} python main.py
fi

exec "$@"
