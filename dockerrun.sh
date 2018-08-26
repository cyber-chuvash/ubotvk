#!/usr/bin/env bash

docker run -d --name ubot --mount type=volume,source=ubotvk-log,dst=/app/log/ --mount type=volume,source=ubotvk-data,dst=/app/data/ --restart unless-stopped ubotvk