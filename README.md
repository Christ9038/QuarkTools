# QuarkTools

## 夸克网盘转存工具

### 使用方法

1.修改`quark.py`中最下方`cookie`为夸克网盘的cookie值，`root_fid`值修改为要保存的目录id。

2.将需要转存的夸克网盘链接保存到`files.txt`文件当中，格式为`<文件夹名称>\t<链接>`

3.执行`python quark.py`后，会在export.txt中生成转存后的文件列表，markdown.md中生成markdown格式的转存列表。