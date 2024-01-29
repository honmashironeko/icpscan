# 开发起因

在挖掘0day的过程中经常遭遇一件繁琐的事情，那就是挖到了0day、写好了批量验证脚本，但是苦于这些资产不知道归属，不知道权重，从而导致白白错过了数量客观的赏金。

作者发现已有的开源工具，几乎都只能对提供的单一域名、固定域名进行查询，实际上无法遍历查询，则会导致遗漏大量站点，例如：api.neko.com.cn 常规工具在面对这条域名的时候，只会查询到 api.neko.com.cn ，这将导致备案查询错误，实际上是 neko.com.cn 才能查到归属，同时又因为 api.neko.com.cn 是api接口没什么访问量，导致权重很低甚至为0，而 neko.com.cn 的权重为6，从而导致遗漏。

又因为无法对IP站点进行查询备案，或大批量进行查询而导致出现大量繁琐的工作，因此决定开发本工具。

# 工具功能

1. 能够对IP、域名、IP:端口、域名:端口四类格式进行查询归属，无需主动分类
2. 能够对IP类型的站点反查域名（目前获取IP的前10个域名）并查询归属
3. 能够对多级域名遍历查询归属，不放过任何一个可能（后续将增加遍历查询权重功能）
4. 能够生成表格文件方便查看结果
5. 采用各种优化代码，大幅度优化查询速度
6. 无需登录任何账号、获取任何Cookie

# 使用帮助

[在仓库中下载最新版本的工具](https://github.com/honmashironeko/icpscan/releases)

请根据自己的chrome版本下载对应驱动（版本没有完全一致也没事），将下载的驱动放置在icpscan.py的相同路径下（请注意操作系统）

[访问网站下载驱动](https://googlechromelabs.github.io/chrome-for-testing/)

![image-20240129154045942](https://github.com/honmashironeko/icpscan/assets/139044047/a11a7296-3956-4e79-947f-d7d65931b826)


![image-20240129154118033](https://github.com/honmashironeko/icpscan/assets/139044047/512f4a11-072f-4692-a112-03d167bfe645)


完成后就可以在cmd中执行：`python icpscan.py -f 文件名` 最后在相同路径下的文件夹查看Excel表格

# 联系方式

关注微信公众号：**樱花庄的本间白猫**

![樱花庄_搜索联合传播样式-标准色版](https://github.com/honmashironeko/icpscan/assets/139044047/444fffd7-f377-4a4f-9a5a-8c8ebf069dc7)
