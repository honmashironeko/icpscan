# 开发起因

在挖掘0day的过程中经常遭遇一件繁琐的事情，那就是挖到了0day、写好了批量验证脚本，但是苦于这些资产不知道归属，不知道权重，从而导致白白错过了数量客观的赏金。

作者发现已有的开源工具，几乎都只能对提供的单一域名、固定域名进行查询，实际上无法遍历查询，则会导致遗漏大量站点，例如：api.neko.com.cn 常规工具在面对这条域名的时候，只会查询到 api.neko.com.cn ，这将导致备案查询错误，实际上是 neko.com.cn 才能查到归属，同时又因为 api.neko.com.cn 是api接口没什么访问量，导致权重很低甚至为0，而 neko.com.cn 的权重为6，从而导致遗漏。

又因为无法对IP站点进行查询备案，或大批量进行查询而导致出现大量繁琐的工作，因此决定开发本工具。

# 工具功能

1. 能够对IP、域名、IP:端口、域名:端口四类格式进行查询归属，无需主动分类。
2. 能够对IP类型的站点反查域名（目前获取IP的前10个域名）并查询归属。
3. 能够对主域名查询归属。
4. 能够生成表格文件方便查看结果。
5. 采用各种优化代码，大幅度优化查询速度。
6. 无需登录任何账号、获取任何Cookie。
7. 自动检测更新，并输出提醒。

# 使用帮助

![Clip_2024-04-22_10-52-02](https://github.com/honmashironeko/icpscan/assets/139044047/7be9f006-ba8d-4d6e-aa1b-98b145114cf3)


`python icpscan.py -f 文件名` 在相同路径下的文件夹查看Excel表格

如果遇到FOFA每日查询上限，可通过-p指定代理地址访问，或采用Zoomeye的API-KEY，使用Zoomeye进行查询。

如果需要查询备案的同时查询权重，可以增加-qz参数，请注意会大幅度降低查询速度。

![Clip_2024-04-22_11-04-18](https://github.com/honmashironeko/icpscan/assets/139044047/729543cb-205b-4d97-a2b5-85b793ba88fd)

![Clip_2024-04-22_11-11-56](https://github.com/honmashironeko/icpscan/assets/139044047/45ee0fc1-8938-463b-a30b-c6f91aa74476)



# 联系方式

关注微信公众号：**樱花庄的本间白猫**

![樱花庄_搜索联合传播样式-标准色版](https://github.com/honmashironeko/icpscan/assets/139044047/af4bffb2-8b26-4846-b7b1-edbb86d3ee7e)

