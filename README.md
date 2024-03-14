# 开发起因

在挖掘0day的过程中经常遭遇一件繁琐的事情，那就是挖到了0day、写好了批量验证脚本，但是苦于这些资产不知道归属，不知道权重，从而导致白白错过了数量客观的赏金。

因为无法对IP站点进行查询备案，或大批量进行查询而导致出现大量繁琐的工作，因此决定开发本工具。

# 工具功能

1. 能够对IP、域名、IP:端口、域名:端口四类格式进行查询归属，无需主动分类
2. 能够对IP类型的站点反查域名（目前获取IP的前10个域名）并查询归属
3. 能够对子域名、主域名进行权重查询，最大化获取关键权重。
4. 能够生成表格文件方便查看结果
5. 采用各种优化代码，大幅度优化查询速度
6. 无需登录任何账号、获取任何Cookie

# 使用帮助

[在仓库中下载最新版本的工具](https://github.com/honmashironeko/icpscan/releases)

请根据自己的chrome版本下载对应驱动（版本没有完全一致也没事），将下载的驱动放置在icpscan.py的相同路径下（请注意操作系统）

[访问网站下载驱动](https://googlechromelabs.github.io/chrome-for-testing/)

![image-20240129154045942](https://github.com/honmashironeko/icpscan/assets/139044047/a11a7296-3956-4e79-947f-d7d65931b826)


![image-20240129154118033](https://github.com/honmashironeko/icpscan/assets/139044047/512f4a11-072f-4692-a112-03d167bfe645)

解压出来先安装第三方库，执行命令 pip install -r requirements.txt ,

完成后就可以在cmd中执行：`python icpscan.py -f 文件名` 

执行完FOFA反查后会进入查询备案阶段，此处会弹出新的cmd及web页面，请在此处点击搜索并通过验证码（如果卡住了请直接刷新web页面，垃圾创宇盾）

![Clip_2024-03-14_15-39-29](https://github.com/honmashironeko/icpscan/assets/139044047/cf62ce06-bbb2-4386-a3b0-cddf62007ec2)

当看到出现 “已写入值到 token.txt 文件”，并且进程停止之后，返回原先启动的cmd，输入回车键继续运行（请注意垃圾创宇盾会导致请求非常慢，请耐心等待）

![Clip_2024-03-14_15-41-28](https://github.com/honmashironeko/icpscan/assets/139044047/b49cbcd3-a177-42be-ac94-a8af669ea08c)

![Clip_2024-03-14_15-48-55](https://github.com/honmashironeko/icpscan/assets/139044047/d39d8e54-ad03-40e4-af72-199d991c6b15)


# 联系方式

关注微信公众号：**樱花庄的本间白猫**

![樱花庄_搜索联合传播样式-标准色版](https://github.com/honmashironeko/icpscan/assets/139044047/444fffd7-f377-4a4f-9a5a-8c8ebf069dc7)
