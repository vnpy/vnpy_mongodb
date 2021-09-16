# vn.py框架的MongoDB数据库接口

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.0.0-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.7-blue.svg" />
</p>

## 说明

基于pymongo开发的MongoDB数据库接口。

## 使用

MongoDB在VN Trader中配置时，需要填写以下字段信息：

| 字段名                                    | 值 |          是否必填|
|---------                                 |---- |  ---|
|database.driver                           | "mongodb" | 必填 |
|database.host                             | 地址| 必填 |
|database.port                             | 端口| 必填 |
|database.database                         | 数据库名| 必填 |
|database.user                             | 用户名| 可选 |
|database.password                         | 密码| 可选 | 
|database.database.authentication_source   | [创建用户所用的数据库][AuthSource]| 可选 | 

 
MongoDB的例子如下所示：

| 字段名             | 值 |
|---------           |----  |
|database.driver     | mongodb |
|database.host       | localhost |
|database.port       | 27017 |
|database.database   | vnpy |
|database.user       | root |
|database.password   | .... |
|database.authentication_source   | vnpy |
