# VeighNa框架的MongoDB数据库接口

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.0.4-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.7|3.8|3.9|3.10-blue.svg" />
</p>

## 说明

基于pymongo 4.1.1 开发的MongoDB数据库接口。

## 使用

在VeighNa中使用MongoDB时，需要在全局配置中填写以下字段信息：

|名称|含义|必填|举例|
|---------|----|---|---|
|database.name|名称|是|mongodb|
|database.host|地址|是|localhost|
|database.port|端口|是|27017|
|database.database|实例|是|vnpy|
|database.user|用户名|否||
|database.password|密码|否||
