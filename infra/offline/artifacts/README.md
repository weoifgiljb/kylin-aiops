# 外部二进制清单

此目录不提交大文件。打包前放入与目标 CANN/JDK 兼容且已核验 SHA-256 的 `opentelemetry-javaagent.jar`、MindSpore wheel、模型 checkpoint 和必要的容器镜像。所有内容由 `prepare-bundle.sh` 写入 `SHA256SUMS`，离线安装时强制校验。
