![扫码_搜索联合传播样式-标准色版](https://github.com/honmashironeko/icpscan/assets/139044047/52ac67e6-1f73-424d-bf00-7d5e5aa5d23c)

![image](https://github.com/honmashironeko/icpscan/assets/139044047/9b74a394-9daf-4834-b4aa-db2ff276e5ac)

开发本工具的主旨是批量对ip、域名资产查询备案信息，为大规模扫描提供帮助。
当前已支持循环测试域名，例如api.qq.baidu.com，可依次查询api.qq.baidu.com、qq.baidu.com、baidu.com的备案信息，为避免遗漏备案！
该工具无需配置账号，到手即用，白嫖查询！

如果对本工具有建议或BUG反馈，请关注微信公众号：樱花庄的本间白猫，加入微信群反馈。

使用帮助
python icpscan.py -h 查看帮助

pip install -r requirements.txt安装必须的环境

执行  python icpscan.py -f 指定txt文件 -c 指定cookie

由于v0.5版本采用了https://www.beianx.cn/  的备案查询，因此需要获取一下他的cookie，但是非必须项，这个站点更加精准而已。
请提供acw_sc__v2=后面的参数到-c中  例如 -c 657c05dbcac**941933******3b6d6891c511d96
![image](https://github.com/honmashironeko/icpscan/assets/139044047/31100981-467b-442c-943e-8c05f7e327c9)

![image](https://github.com/honmashironeko/icpscan/assets/139044047/54ba2460-2f79-4972-91be-cdd3e6b4d090)
