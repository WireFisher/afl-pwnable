# XCTF 2017 API Tools

## 配置
文件名：`config.json`
```json
{
	"token": "FHEMOWhuPGVRyRb7H4V4cKtpwupoYF8l",
	"challenges_url": "http://202.112.51.152:5000/challenges",
	"directory": "/tmp/work"
}
```
此配置文件由两个脚本共用，其中`directory`为程序的工作目录，**需指定为绝对路径**。



## 题目爬取
文件名：`crawler.py`  
此脚本应该定时启动。其从给定的 URL 爬取题目信息并下载。每道题将建立以其`name`属性命名的文件夹，层级如下：
```
challenge_name/
    chanllenge_name # 二进制文件
    metadata.json # 题目信息（如服务器信息等）
```
如文件夹中已经存在这些文件，爬虫将比较获取到的信息和已有的是否相符，如果不同，则使用新文件覆盖老的。

## 题目提交
文件名：`submitter.py`  
此脚本也应该定时启动，其从每个题目目录下（判断依据为目录下有`metadata.json`）寻找`payload.bin.*`文件，并将其提交给元数据中指定的服务器。  
注意：此脚本将`payload.bin.*`依次地完全以二进制脚本的形式传送给服务器。  
每次提交的核心逻辑：
```python
try:
    nc = nclib.Netcat((server['ip'], server['port']), verbose=False)
    nc.settimeout(5)
    result = nc.recv_until('Token:'.encode()) # 对方会首先请求 token
    nc.send((token + '\n').encode()) # 发送 token 并确认
    nc.send(payload) # 发送 payload.bin 的所有内容
    nc.recv_until('detected'.encode()) # 检测是否存在 detected 字样
    print('"detected" found. Success!') # 存在则解题成功
    return True

except ValueError:
    print('"detected" not found. Failure!') # 否则解题失败
    return False
```
每道题只要有一台服务器的提交判断为成功则为成功，脚本将在题目目录下新建`payload.bin.xxxxxxxx.success`并写入成功时间，之后的运行过程中，将忽略该目录。




