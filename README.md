# BlogOnlineEditor
一款极其轻量化的面向Hugo博客的在线编辑器
[原始开发诉求](https://hiyyq.cn/posts/20220403011131)

## 功能列表
- 支持在线创建，修改，删除博客文章
- 支持在线上传图片
- 支持删除已上传但未引用到的图片
- 支持查看文章变更
- 支持多窗口编辑不同文章，不支持多窗口编辑同一文章

## 注意事项
- 仅支持Markdown文件在形如`content/posts/XXX/index.md`下，并且图片与md文件同级的场景
- 所有图片文件上传后均会自动更名为UUID存放在文章目录下
- 系统没有登录认证校验

## 快速使用
```shell
pip3 install flask,pyyaml
```

```shell
export BLOG_GIT_SSH = "Hugo博客站点的代码仓，需要提前配置git ssh免密"
export CMD_AFTER_PUSH = "在进行git push后自动执行的脚本路径，通常用于串联自动部署流程"
python3 app.py
```

## 实现原理
- git clone 拉下远端博客文章库
- 在线创建，修改，删除博客文章
- git commit && git push 将文章改动推送到远端
- 调用自定义脚本拉取远端库重新生成静态站点部署

## 技术栈清单
- Git
- Python3
- Vue2
- Vditor
- Bootstrap
- Flask
- Axios

本项目源码极其简单，可以随意修改源码进行二次开发直至满足你的诉求，也欢迎提PR。