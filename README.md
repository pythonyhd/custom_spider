# custom_spider

* 中国执行信息公开网-三大维度数据抓取

##### [介绍文档](https://github.com/pythonyhd/custom_spider/README.md)

* 支持版本: ![](https://img.shields.io/badge/Python-3.x-blue.svg)

### 下载安装

* 下载源码:

```
https://github.com/pythonyhd/custom_spider
```

* 安装依赖:

```shell
pip install -r requirements.txt
```

### 使用方法

    * 首先您需要获取一批搜索关键词放到redis数据库当中
    * 程序会根据关键词进行搜索，获取全部数据
    * 本项目支持MySQL数据库，mongodb数据库，MySQL支持异步存储
    * 验证码识别不做过多介绍，大概流程如下：
        * 获取验证码训练集
        * 处理验证码(二值化、去除噪点)
        * 分割字符，将验证码分割成单字符的图片(垂直投影法、连通域法、水滴法...),将分割后的单字符进行分类
        * 读取单字符图片的特征值和验证码正确值的标签
        * 利用sklearn包，训练模型,并保存训练结果
        * 利用训练好的模型，对验证码进行识别

### 问题反馈

　　任何问题欢迎在[Issues](https://github.com/pythonyhd/custom_spider/issues) 中反馈。

　　你的反馈会让此项目变得更加完美。

### 贡献代码

　　本项目依然不够完善，如果发现bug或有新的功能添加，请在[Issues](https://github.com/pythonyhd/custom_spider/issues)中提交bug(或新功能)描述，在确认后提交你的代码。

---

### TODO
- [x] 兼容py2

---


### 赞助作者
甲鱼说，咖啡是灵魂的饮料，买点咖啡

[谢谢这些人的☕️](./coffee.md)

直接转账打赏作者的辛苦劳动：

<img src="https://i.imgur.com/lzM8sPs.png" width="250" />