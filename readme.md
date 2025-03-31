本程序提供了两种方式获取文章信息链接，也提供了从文章信息链接下载文章文件的功能。

本程序使用了 selenium，需要浏览器的 webdriver 才能工作，比如【chrome web driver 下载地址】

若出现`ModuleNotFoundError: No module named blinker._saferef` 可能是由于你的 blinker 版本过高，selenium 需要重新安装 blinker==1.7.0 版本。