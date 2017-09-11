# afl-pwnable

## 功能

- [ ] 任务调度：不用复杂，简单一点
- [ ] 题目信息抓取
- [ ] testcase生成器
- [ ] AFL漏洞挖掘
- [ ] PoC提交

## 运行说明
0. 先在docker运行的宿主机中执行`home`目录下的`prelude`，（以root权限执行）。
0. 启动docker，进入docker。
0. 在docker中执行`source ~/fuzzer/bin/activate`，导入virtualenv的环境。
0. 执行` python ~/Code/afl-pwnable/fuzzer-scheduling/scheduling.py`，启动执行，工作目录默认为`/tmp/work`。