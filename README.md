# Mamba-Web-Manager  

## ✨这是啥？  
说白了就是个web版的精致WebShell。  
传统木马管理工具预览文件、上传下载、命令执行都不太方便，还容易卡死。  
  
这个工具解决了这些问题：  

- 界面干净清爽，用起来不费劲  
- 操作文件跟Windows资源管理器一样顺手  
- 执行命令输出完整，不用担心输出不全、编码问题  
- 具有基础隐蔽性，直接访问开启的端口默认是404
## ✨为啥做这个？  
木马管理经常让我抓狂：  

文件操作折腾半天  
执行命令输出不全  
操作界面不够美观  

实在难受，自己写个更方便的隐蔽文件管理器。  

## ✨主要功能  

### 文件管理  
- 像电脑一样浏览服务器文件  
- 直接预览图片、视频、代码、文本文档  
- 易于上传下载，支持拖拽  
- 文件大小自动换算  
  
![image](https://github.com/user-attachments/assets/7d654d00-1dbd-4f23-b6b5-493c01521fd9)

  
### 命令执行
- 简洁美观的命令执行区  
- 命令超时10秒自动终止  
- 完整显示命令输出和错误  
  
![image](https://github.com/user-attachments/assets/62fffc93-d44f-4b58-a3ab-9fd34a01b84b)

  
## ✨怎么用？
### 安装依赖（就一个命令）：  
pip install flask  
### 启动服务（建议用非常规端口）：  
python mambaweb.py -p 54321 -d d://  
【若执行python mambaweb.py，会默认打开D盘和81端口】  
### 浏览器访问：  
http://目标IP:54321/mamba  
http://目标IP:54321/mamba/out  
账号密码默认都是a 
### 建议打包成EXE使用

## ⚠️安全提醒
用完记得及时结束进程
记得更改默认密码和默认路径  
仅供研究学习，未授权使用造成的后果与作者无关 

### 🔗项目地址：https://github.com/YueNanWangZi/Mamba-Web-Manager
### 💡希望大家多提issue。  
