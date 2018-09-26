# UbotVK

``` bash
$ wget https://github.com/cyber-chuvash/ubotvk/releases/download/v1.1/ubotvk.tar
$ docker load < ubotvk.tar
$ docker run -d --name ubot \
--mount type=volume,source=ubotvk-log,dst=/app/log/ \
--mount type=volume,source=ubotvk-data,dst=/app/data/ \
--restart unless-stopped \
-e VK_LOGIN="+79991112233" \
-e VK_PASS="pa$$w0rd" \
-e UBOTVK_INST_FEAT="pidors,hardbass" \
-e UBOTVK_LOG_LEVEL="WARNING" \
ubotvk
```
