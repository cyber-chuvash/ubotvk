# UbotVK
[![Build Status](https://travis-ci.org/cyber-chuvash/ubotvk.svg?branch=master)](https://travis-ci.org/cyber-chuvash/ubotvk)

``` bash
$ docker pull cyberchuvash/ubotvk
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
